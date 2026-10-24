import math
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

MONTHS_ES = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
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


if __name__ == "__main__":
    app.run(debug=True)
