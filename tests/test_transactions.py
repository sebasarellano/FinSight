"""Pruebas del registro de movimientos y del cálculo de saldos."""

import pytest

import database
from app import get_account_balances


def valid_form(**changes):
    """Formulario válido de referencia; cada prueba cambia solo lo suyo."""
    form = {
        "description": "Almuerzo de prueba",
        "amount": "10.50",
        "transaction_type": "expense",
        "category": "Alimentación",
        "transaction_date": "2026-10-24",
        "account_id": "1",
    }
    form.update(changes)
    return form


def count_transactions():
    """Cuenta los movimientos guardados en la base temporal."""
    connection = database.get_db_connection()

    try:
        return connection.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]
    finally:
        connection.close()


def test_dashboard_loads(client):
    response = client.get("/")

    assert response.status_code == 200


def test_valid_transaction_is_saved(client):
    response = client.post("/transactions", data=valid_form())

    # La ruta redirige (302) después de guardar.
    assert response.status_code == 302
    assert count_transactions() == 1


@pytest.mark.parametrize(
    "amount",
    ["", "abc", "0", "-5", "nan", "inf", "10,50"],
)
def test_invalid_amount_is_rejected(client, amount):
    client.post("/transactions", data=valid_form(amount=amount))

    assert count_transactions() == 0


def test_invalid_date_is_rejected(client):
    client.post(
        "/transactions",
        data=valid_form(transaction_date="2026-13-45"),
    )

    assert count_transactions() == 0


def test_unknown_account_is_rejected(client):
    client.post("/transactions", data=valid_form(account_id="999"))

    assert count_transactions() == 0


def test_balance_reflects_income_and_expense(client):
    client.post(
        "/transactions",
        data=valid_form(
            amount="100",
            transaction_type="income",
            category="Salario",
        ),
    )
    client.post("/transactions", data=valid_form(amount="40"))

    # La cuenta 1 ("Efectivo") empieza con 325,50: 325,50 + 100 - 40.
    cash = next(a for a in get_account_balances() if a["id"] == 1)

    assert cash["balance"] == pytest.approx(385.50)