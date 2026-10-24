
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


def get_accounts():
    """Obtiene las cuentas disponibles."""
    connection = get_db_connection()

    try:
        return connection.execute(
            "SELECT id, name FROM accounts ORDER BY name"
        ).fetchall()
    finally:
        connection.close()


def get_transactions():
    """Obtiene los movimientos junto con el nombre de su cuenta."""
    connection = get_db_connection()

    try:
        return connection.execute(
            """
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
        ).fetchall()
    finally:
        connection.close()


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        amount_text = request.form.get("amount", "").strip()
        transaction_type = request.form.get("transaction_type", "").strip()
        category = request.form.get("category", "").strip()
        transaction_date = request.form.get("transaction_date", "").strip()
        account_id_text = request.form.get("account_id", "").strip()

        # Validar que los campos de texto estén completos.
        if not description or len(description) > 120:
            flash(
                "La descripción es obligatoria y no puede superar "
                "los 120 caracteres.",
                "error",
            )
            return redirect(url_for("transactions"))

        if category not in CATEGORIES:
            flash("Selecciona una categoría válida.", "error")
            return redirect(url_for("transactions"))

        if transaction_type not in ("income", "expense"):
            flash("Selecciona un tipo de movimiento válido.", "error")
            return redirect(url_for("transactions"))

        # Convertir y validar el importe.
        try:
            amount = float(amount_text)
        except ValueError:
            amount = 0

        if not math.isfinite(amount) or amount <= 0:
            flash("El importe debe ser un número mayor que cero.", "error")
            return redirect(url_for("transactions"))

        # Validar la fecha.
        try:
            parsed_date = date.fromisoformat(transaction_date)
        except ValueError:
            flash("Introduce una fecha válida.", "error")
            return redirect(url_for("transactions"))

        # Validar el identificador de la cuenta.
        try:
            account_id = int(account_id_text)
        except ValueError:
            flash("Selecciona una cuenta válida.", "error")
            return redirect(url_for("transactions"))

        connection = get_db_connection()

        try:
            account = connection.execute(
                "SELECT id FROM accounts WHERE id = ?",
                (account_id,),
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
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    description,
                    amount,
                    transaction_type,
                    category,
                    parsed_date.isoformat(),
                    account_id,
                ),
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


if __name__ == "__main__":
    app.run(debug=True)
