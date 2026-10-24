import math
import re
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for

from database import get_db_connection, initialize_database

app = Flask(__name__)
app.secret_key = "clave-local-de-desarrollo"

# Asegura que la estructura de la base de datos exista al iniciar.
initialize_database()

CATEGORIES = [
    "Salario",
    "Ventas",
    "Alimentación",
    "Transporte",
    "Vivienda",
    "Servicios",
    "Salud",
    "Educación",
    "Entretenimiento",
    "Otros",
]

# Categorías que representan ingresos: no tienen presupuesto de gasto.
INCOME_CATEGORIES = ("Salario", "Ventas")

# Categorías que se pueden presupuestar (las de gasto).
EXPENSE_CATEGORIES = [
    category for category in CATEGORIES
    if category not in INCOME_CATEGORIES
]

MONTHS_ES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

MONTH_NAMES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Cómo se presenta cada tipo de cuenta en el dashboard:
# (símbolo, clase CSS del icono, subtítulo).
ACCOUNT_STYLES = {
    "cash": ("$", "account-cash", "Disponible"),
    "bank": ("▤", "account-bank", "Cuenta corriente"),
    "savings": ("◇", "account-savings", "Reserva personal"),
    "other": ("•", "account-bank", "Otra cuenta"),
}

# Nombre legible de cada tipo de cuenta (páginas de cuentas).
ACCOUNT_TYPE_LABELS = {
    "cash": "Efectivo",
    "bank": "Cuenta bancaria",
    "savings": "Ahorros",
    "other": "Otra cuenta",
}

# Tope razonable para un saldo inicial (en valor absoluto).
MAX_INITIAL_BALANCE = 1_000_000_000

# Tope razonable para el límite de un presupuesto mensual.
MAX_BUDGET_AMOUNT = 1_000_000

# A partir de este porcentaje de uso, un presupuesto se considera
# "cerca del límite". A partir del 100 % se considera superado.
BUDGET_WARNING_PERCENT = 80


# ---------------------------------------------------------------
# Filtros de plantilla: cambian solo cómo se muestra un valor.
# ---------------------------------------------------------------
@app.template_filter("money")
def format_money(value):
    """Convierte 8425.5 en '8.425,50' (formato español)."""
    value = round(float(value or 0), 2)
    sign = "-" if value < 0 else ""
    text = f"{abs(value):,.2f}"  # '8,425.50'
    # Intercambiar separadores usando un marcador temporal.
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return sign + text


@app.template_filter("percent")
def format_percent(value):
    """Convierte 47.69 en '47,7 %'."""
    return f"{float(value):.1f}".replace(".", ",") + " %"


@app.template_filter("short_date")
def format_short_date(value):
    """Convierte '2026-10-24' en '24 oct 2026'."""
    parsed = date.fromisoformat(value)
    return f"{parsed.day} {MONTHS_ES[parsed.month - 1]} {parsed.year}"


@app.template_filter("month_label")
def format_month_label(value):
    """Convierte '2026-10' en 'octubre 2026'."""
    year, month = value.split("-")
    return f"{MONTH_NAMES_ES[int(month) - 1]} {year}"


# ---------------------------------------------------------------
# Consultas a la base de datos
# ---------------------------------------------------------------
def get_accounts():
    """Obtiene las cuentas disponibles."""
    connection = get_db_connection()

    try:
        return connection.execute(
            "SELECT id, name FROM accounts ORDER BY name"
        ).fetchall()
    finally:
        connection.close()


def get_transactions(limit=None):
    """Obtiene los movimientos junto con el nombre de su cuenta.

    Si se indica 'limit', devuelve solo los más recientes.
    """
    query = """
        SELECT
            transactions.id,
            transactions.description,
            transactions.amount,
            transactions.transaction_type,
            transactions.category,
            transactions.transaction_date,
            accounts.name AS account_name
        FROM transactions
        JOIN accounts
            ON transactions.account_id = accounts.id
        ORDER BY
            transactions.transaction_date DESC,
            transactions.id DESC
    """
    parameters = ()

    if limit is not None:
        query += " LIMIT ?"
        parameters = (limit,)

    connection = get_db_connection()

    try:
        return connection.execute(query, parameters).fetchall()
    finally:
        connection.close()


def get_transaction(transaction_id):
    """Obtiene un movimiento por su id, o None si no existe."""
    connection = get_db_connection()

    try:
        return connection.execute(
            """
            SELECT
                id,
                description,
                amount,
                transaction_type,
                category,
                transaction_date,
                account_id
            FROM transactions
            WHERE id = ?
            """,
            (transaction_id,),
        ).fetchone()
    finally:
        connection.close()


def get_account_balances():
    """Calcula el saldo actual de cada cuenta.

    saldo = saldo inicial
            + ingresos
            - gastos
            - transferencias enviadas
            + transferencias recibidas
    """
    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                a.id,
                a.name,
                a.account_type,
                a.initial_balance,
                a.initial_balance
                + COALESCE((
                    -- Movimientos de esta cuenta: los ingresos suman;
                    -- los gastos y las transferencias enviadas restan.
                    SELECT SUM(
                        CASE t.transaction_type
                            WHEN 'income' THEN t.amount
                            ELSE -t.amount
                        END
                    )
                    FROM transactions t
                    WHERE t.account_id = a.id
                ), 0)
                + COALESCE((
                    -- Transferencias que llegan a esta cuenta.
                    SELECT SUM(t.amount)
                    FROM transactions t
                    WHERE t.transaction_type = 'transfer'
                      AND t.destination_account_id = a.id
                ), 0) AS balance
            FROM accounts a
            ORDER BY a.id
            """
        ).fetchall()
    finally:
        connection.close()

    return [dict(row) for row in rows]


def get_account(account_id):
    """Devuelve una cuenta (con su saldo actual) o None si no existe."""
    for account in get_account_balances():
        if account["id"] == account_id:
            return account
    return None


def get_budget_progress(month_key):
    """Obtiene los presupuestos de un mes (formato 'AAAA-MM') con su avance.

    Para cada presupuesto calcula lo gastado en esa categoría y ese mes
    (solo gastos: las transferencias no cuentan), lo que queda disponible,
    el porcentaje usado y su estado:
    - 'ok': por debajo del umbral de aviso.
    - 'warning': cerca del límite.
    - 'over': límite alcanzado o superado.
    """
    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                b.id,
                b.category,
                b.month,
                b.amount,
                COALESCE(SUM(t.amount), 0) AS spent
            FROM budgets b
            LEFT JOIN transactions t
                ON t.category = b.category
               AND t.transaction_type = 'expense'
               AND strftime('%Y-%m', t.transaction_date) = b.month
            WHERE b.month = ?
            GROUP BY b.id
            ORDER BY b.category
            """,
            (month_key,),
        ).fetchall()
    finally:
        connection.close()

    budgets = []

    for row in rows:
        limit_amount = float(row["amount"])
        spent = round(float(row["spent"]), 2)
        used_percent = spent / limit_amount * 100

        if used_percent >= 100:
            status = "over"
        elif used_percent >= BUDGET_WARNING_PERCENT:
            status = "warning"
        else:
            status = "ok"

        budgets.append({
            "id": row["id"],
            "category": row["category"],
            "month": row["month"],
            "amount": limit_amount,
            "spent": spent,
            "remaining": round(limit_amount - spent, 2),
            "used_percent": used_percent,
            # La barra nunca pasa del 100 % aunque el gasto lo supere.
            "bar_width": min(used_percent, 100),
            "status": status,
        })

    return budgets


def get_month_summary(month_key):
    """Suma ingresos y gastos de un mes (formato 'AAAA-MM').

    Las transferencias no se incluyen: no son ingresos ni gastos.
    """
    connection = get_db_connection()

    try:
        row = connection.execute(
            """
            SELECT
                COALESCE(SUM(
                    CASE WHEN transaction_type = 'income'
                         THEN amount END
                ), 0) AS income,
                COALESCE(SUM(
                    CASE WHEN transaction_type = 'expense'
                         THEN amount END
                ), 0) AS expense
            FROM transactions
            WHERE strftime('%Y-%m', transaction_date) = ?
            """,
            (month_key,),
        ).fetchone()
    finally:
        connection.close()

    return row["income"], row["expense"]


def get_monthly_cash_flow(today=None):
    """Obtiene ingresos y gastos de los últimos seis meses.

    Incluye el mes actual, incluso si todavía no tiene movimientos.
    Las transferencias no se consideran ingresos ni gastos.
    """
    if today is None:
        today = date.today()

    # Convertir año y mes a un índice para calcular los seis meses
    # sin errores cuando el período cruza de diciembre a enero.
    current_month_index = today.year * 12 + today.month - 1
    first_month_index = current_month_index - 5

    start_year = first_month_index // 12
    start_month = first_month_index % 12 + 1
    start_date = date(start_year, start_month, 1)

    next_month_index = current_month_index + 1
    end_year = next_month_index // 12
    end_month = next_month_index % 12 + 1
    end_date = date(end_year, end_month, 1)

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                strftime('%Y-%m', transaction_date) AS month,
                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'income' THEN amount
                            ELSE 0
                        END
                    ), 0
                ) AS income,
                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'expense' THEN amount
                            ELSE 0
                        END
                    ), 0
                ) AS expense
            FROM transactions
            WHERE transaction_date >= ?
              AND transaction_date < ?
              AND transaction_type IN ('income', 'expense')
            GROUP BY strftime('%Y-%m', transaction_date)
            """,
            (start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    finally:
        connection.close()

    # Indexar los resultados para localizar cada mes fácilmente.
    monthly_totals = {
        row["month"]: {
            "income": float(row["income"]),
            "expense": float(row["expense"]),
        }
        for row in rows
    }

    # Crear los seis meses, incluidos los que no tengan movimientos.
    months = []

    for offset in range(6):
        month_index = first_month_index + offset
        year = month_index // 12
        month_number = month_index % 12 + 1
        month_key = f"{year:04d}-{month_number:02d}"

        totals = monthly_totals.get(
            month_key,
            {"income": 0.0, "expense": 0.0},
        )

        months.append({
            "month": MONTHS_ES[month_number - 1],
            "income": totals["income"],
            "expense": totals["expense"],
            "is_current": month_key == today.strftime("%Y-%m"),
        })

    # Usar una misma escala para comparar ingresos y gastos.
    maximum = max(
        (max(month["income"], month["expense"]) for month in months),
        default=0,
    )

    for month in months:
        if maximum > 0:
            month["income_height"] = month["income"] / maximum * 100
            month["expense_height"] = month["expense"] / maximum * 100
        else:
            month["income_height"] = 0
            month["expense_height"] = 0

    return months

# ---------------------------------------------------------------
# Validación de formularios
# ---------------------------------------------------------------
def parse_transaction_form(form):
    """Valida los datos del formulario (crear y editar usan lo mismo).

    Devuelve una tupla (valores, error):
    - si todo es válido: (diccionario con los valores limpios, None)
    - si algo falla: (None, mensaje de error para el usuario)
    """
    description = form.get("description", "").strip()
    amount_text = form.get("amount", "").strip()
    transaction_type = form.get("transaction_type", "").strip()
    category = form.get("category", "").strip()
    transaction_date = form.get("transaction_date", "").strip()
    account_id_text = form.get("account_id", "").strip()

    if not description or len(description) > 120:
        return None, (
            "La descripción es obligatoria y no puede superar "
            "los 120 caracteres."
        )

    if category not in CATEGORIES:
        return None, "Selecciona una categoría válida."

    if transaction_type not in ("income", "expense"):
        return None, "Selecciona un tipo de movimiento válido."

    # Convertir y validar el importe.
    try:
        amount = float(amount_text)
    except ValueError:
        amount = 0

    if not math.isfinite(amount) or amount <= 0:
        return None, "El importe debe ser un número mayor que cero."

    # Validar la fecha.
    try:
        parsed_date = date.fromisoformat(transaction_date)
    except ValueError:
        return None, "Introduce una fecha válida."

    # Validar el identificador de la cuenta.
    try:
        account_id = int(account_id_text)
    except ValueError:
        return None, "Selecciona una cuenta válida."

    values = {
        "description": description,
        "amount": amount,
        "transaction_type": transaction_type,
        "category": category,
        "transaction_date": parsed_date.isoformat(),
        "account_id": account_id,
    }
    return values, None


def parse_account_form(form):
    """Valida los datos del formulario de una cuenta.

    Devuelve (valores, error), igual que parse_transaction_form.
    El saldo inicial puede ser negativo (una cuenta con deuda).
    """
    name = form.get("name", "").strip()
    account_type = form.get("account_type", "").strip()
    balance_text = form.get("initial_balance", "").strip()

    if not name or len(name) > 60:
        return None, (
            "El nombre es obligatorio y no puede superar los 60 caracteres."
        )

    if account_type not in ACCOUNT_TYPE_LABELS:
        return None, "Selecciona un tipo de cuenta válido."

    try:
        initial_balance = float(balance_text)
    except ValueError:
        return None, "El saldo inicial debe ser un número."

    if (
        not math.isfinite(initial_balance)
        or abs(initial_balance) > MAX_INITIAL_BALANCE
    ):
        return None, "El saldo inicial está fuera del rango permitido."

    values = {
        "name": name,
        "account_type": account_type,
        "initial_balance": round(initial_balance, 2),
    }
    return values, None


def is_valid_month(value):
    """Indica si el texto tiene el formato 'AAAA-MM' con un mes real."""
    return re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value) is not None


def parse_budget_form(form):
    """Valida los datos del formulario de un presupuesto.

    Devuelve (valores, error), igual que parse_transaction_form.
    Solo se pueden presupuestar categorías de gasto.
    """
    category = form.get("category", "").strip()
    month = form.get("month", "").strip()
    amount_text = form.get("amount", "").strip()

    if category not in EXPENSE_CATEGORIES:
        return None, "Selecciona una categoría de gasto válida."

    if not is_valid_month(month):
        return None, "Selecciona un mes válido."

    try:
        amount = float(amount_text)
    except ValueError:
        amount = 0

    if not math.isfinite(amount) or amount <= 0 or amount > MAX_BUDGET_AMOUNT:
        return None, (
            "El límite debe ser un número mayor que cero "
            "y no superar 1.000.000."
        )

    values = {
        "category": category,
        "month": month,
        "amount": round(amount, 2),
    }
    return values, None


# ---------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------
@app.route("/")
def home():
    today = date.today()

    # Cuentas con su saldo y su peso dentro del patrimonio.
    accounts = get_account_balances()
    total_balance = round(sum(a["balance"] for a in accounts), 2)

    for account in accounts:
        symbol, css_class, subtitle = ACCOUNT_STYLES[account["account_type"]]
        account["symbol"] = symbol
        account["css_class"] = css_class
        account["subtitle"] = subtitle
        account["share"] = (
            max(account["balance"], 0) / total_balance * 100
            if total_balance > 0
            else 0
        )

    # Resumen del mes actual.
    month_income, month_expense = get_month_summary(today.strftime("%Y-%m"))
    month_net = month_income - month_expense
    savings_rate = (
        month_net / month_income * 100 if month_income > 0 else None
    )

    return render_template(
        "dashboard.html",
        accounts=accounts,
        total_balance=total_balance,
        month_income=month_income,
        month_expense=month_expense,
        month_net=month_net,
        savings_rate=savings_rate,
        recent_transactions=get_transactions(limit=5),
        monthly_cash_flow=get_monthly_cash_flow(today),
    )


@app.route("/accounts")
def accounts():
    """Lista las cuentas con su saldo inicial y su saldo actual."""
    account_rows = get_account_balances()
    total_balance = round(sum(a["balance"] for a in account_rows), 2)

    for account in account_rows:
        symbol, css_class, _ = ACCOUNT_STYLES[account["account_type"]]
        account["symbol"] = symbol
        account["css_class"] = css_class
        account["type_label"] = ACCOUNT_TYPE_LABELS[account["account_type"]]

    return render_template(
        "accounts.html",
        accounts=account_rows,
        total_balance=total_balance,
    )


@app.route("/accounts/<int:account_id>/edit", methods=["GET", "POST"])
def edit_account(account_id):
    account = get_account(account_id)

    if account is None:
        flash("La cuenta que intentas editar no existe.", "error")
        return redirect(url_for("accounts"))

    if request.method == "POST":
        values, error = parse_account_form(request.form)

        if error:
            flash(error, "error")
            return redirect(url_for("edit_account", account_id=account_id))

        values["id"] = account_id

        connection = get_db_connection()

        try:
            # No se permiten dos cuentas con el mismo nombre: el selector
            # de Movimientos mostraría opciones idénticas.
            duplicate = connection.execute(
                """
                SELECT id FROM accounts
                WHERE lower(name) = lower(:name) AND id != :id
                """,
                values,
            ).fetchone()

            if duplicate is not None:
                flash("Ya existe otra cuenta con ese nombre.", "error")
                return redirect(
                    url_for("edit_account", account_id=account_id)
                )

            connection.execute(
                """
                UPDATE accounts
                SET
                    name = :name,
                    account_type = :account_type,
                    initial_balance = :initial_balance
                WHERE id = :id
                """,
                values,
            )
            connection.commit()

        except Exception:
            connection.rollback()
            app.logger.exception("No se pudo actualizar la cuenta")
            flash(
                "No se pudo actualizar la cuenta. Inténtalo de nuevo.",
                "error",
            )
            return redirect(url_for("edit_account", account_id=account_id))

        finally:
            connection.close()

        flash("Cuenta actualizada correctamente.", "success")
        return redirect(url_for("accounts"))

    return render_template(
        "edit_account.html",
        account=account,
        type_labels=ACCOUNT_TYPE_LABELS,
    )


@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    if request.method == "POST":
        values, error = parse_transaction_form(request.form)

        if error:
            flash(error, "error")
            return redirect(url_for("transactions"))

        connection = get_db_connection()

        try:
            account = connection.execute(
                "SELECT id FROM accounts WHERE id = ?",
                (values["account_id"],),
            ).fetchone()

            if account is None:
                flash("La cuenta seleccionada no existe.", "error")
                return redirect(url_for("transactions"))

            connection.execute(
                """
                INSERT INTO transactions (
                    description,
                    amount,
                    transaction_type,
                    category,
                    transaction_date,
                    account_id
                )
                VALUES (
                    :description,
                    :amount,
                    :transaction_type,
                    :category,
                    :transaction_date,
                    :account_id
                )
                """,
                values,
            )
            connection.commit()

        except Exception:
            connection.rollback()
            app.logger.exception("No se pudo guardar el movimiento")
            flash(
                "No se pudo guardar el movimiento. Inténtalo de nuevo.",
                "error",
            )
            return redirect(url_for("transactions"))

        finally:
            connection.close()

        flash("Movimiento registrado correctamente.", "success")
        return redirect(url_for("transactions"))

    return render_template(
        "transactions.html",
        transactions=get_transactions(),
        accounts=get_accounts(),
        categories=CATEGORIES,
        today=date.today().isoformat(),
    )


@app.route("/transactions/<int:transaction_id>/edit", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    transaction = get_transaction(transaction_id)

    # Solo se pueden editar ingresos y gastos. Las transferencias
    # todavía no se crean desde la interfaz.
    if transaction is None or transaction["transaction_type"] == "transfer":
        flash("El movimiento que intentas editar no existe.", "error")
        return redirect(url_for("transactions"))

    if request.method == "POST":
        values, error = parse_transaction_form(request.form)

        if error:
            flash(error, "error")
            return redirect(
                url_for("edit_transaction", transaction_id=transaction_id)
            )

        # El id del movimiento se añade a los valores para el UPDATE.
        values["id"] = transaction_id

        connection = get_db_connection()

        try:
            account = connection.execute(
                "SELECT id FROM accounts WHERE id = ?",
                (values["account_id"],),
            ).fetchone()

            if account is None:
                flash("La cuenta seleccionada no existe.", "error")
                return redirect(
                    url_for("edit_transaction", transaction_id=transaction_id)
                )

            connection.execute(
                """
                UPDATE transactions
                SET
                    description = :description,
                    amount = :amount,
                    transaction_type = :transaction_type,
                    category = :category,
                    transaction_date = :transaction_date,
                    account_id = :account_id
                WHERE id = :id
                """,
                values,
            )
            connection.commit()

        except Exception:
            connection.rollback()
            app.logger.exception("No se pudo actualizar el movimiento")
            flash(
                "No se pudo actualizar el movimiento. Inténtalo de nuevo.",
                "error",
            )
            return redirect(
                url_for("edit_transaction", transaction_id=transaction_id)
            )

        finally:
            connection.close()

        flash("Movimiento actualizado correctamente.", "success")
        return redirect(url_for("transactions"))

    return render_template(
        "edit_transaction.html",
        transaction=transaction,
        accounts=get_accounts(),
        categories=CATEGORIES,
    )


# Eliminar solo acepta POST: una acción que modifica datos no debe
# poder dispararse con un simple enlace (GET).
@app.route("/transactions/<int:transaction_id>/delete", methods=["POST"])
def delete_transaction(transaction_id):
    connection = get_db_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM transactions WHERE id = ?",
            (transaction_id,),
        )
        connection.commit()
        deleted = cursor.rowcount > 0

    except Exception:
        connection.rollback()
        app.logger.exception("No se pudo eliminar el movimiento")
        flash(
            "No se pudo eliminar el movimiento. Inténtalo de nuevo.",
            "error",
        )
        return redirect(url_for("transactions"))

    finally:
        connection.close()

    if deleted:
        flash("Movimiento eliminado correctamente.", "success")
    else:
        flash("El movimiento ya no existe.", "error")

    return redirect(url_for("transactions"))


@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    """Muestra y guarda los presupuestos mensuales por categoría."""
    if request.method == "POST":
        values, error = parse_budget_form(request.form)

        if error:
            flash(error, "error")
            return redirect(url_for("budgets"))

        connection = get_db_connection()

        try:
            # Si ya existe un presupuesto para esa categoría y mes
            # (restricción UNIQUE), se actualiza el importe en lugar
            # de dar error.
            connection.execute(
                """
                INSERT INTO budgets (category, month, amount)
                VALUES (:category, :month, :amount)
                ON CONFLICT (category, month)
                DO UPDATE SET amount = excluded.amount
                """,
                values,
            )
            connection.commit()

        except Exception:
            connection.rollback()
            app.logger.exception("No se pudo guardar el presupuesto")
            flash(
                "No se pudo guardar el presupuesto. Inténtalo de nuevo.",
                "error",
            )
            return redirect(url_for("budgets"))

        finally:
            connection.close()

        flash("Presupuesto guardado correctamente.", "success")
        return redirect(url_for("budgets", month=values["month"]))

    # Mes que se está consultando: el de la dirección (?month=AAAA-MM)
    # si es válido; si no, el mes actual.
    selected_month = request.args.get("month", "").strip()

    if not is_valid_month(selected_month):
        selected_month = date.today().strftime("%Y-%m")

    return render_template(
        "budgets.html",
        budgets=get_budget_progress(selected_month),
        categories=EXPENSE_CATEGORIES,
        selected_month=selected_month,
        warning_percent=BUDGET_WARNING_PERCENT,
    )


if __name__ == "__main__":
    app.run(debug=True)