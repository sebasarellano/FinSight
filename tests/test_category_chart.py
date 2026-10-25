"""Pruebas de la distribución de gastos por categoría."""

import pytest

from app import get_expense_by_category


def test_groups_expenses_by_category(client, add_transaction):
    add_transaction(
        amount="10", category="Alimentación", transaction_date="2026-10-02"
    )
    add_transaction(
        amount="15", category="Alimentación", transaction_date="2026-10-20"
    )
    add_transaction(
        amount="30", category="Transporte", transaction_date="2026-10-05"
    )

    result = get_expense_by_category("2026-10")

    # Ordenado de mayor a menor gasto.
    assert [(i["category"], i["total"]) for i in result] == [
        ("Transporte", 30.0),
        ("Alimentación", 25.0),
    ]
    assert result[0]["percent"] == pytest.approx(30 / 55 * 100)


def test_ignores_income_and_other_months(client, add_transaction):
    add_transaction(
        amount="900", transaction_type="income", category="Salario",
        transaction_date="2026-10-01",
    )
    add_transaction(amount="40", transaction_date="2026-09-15")
    add_transaction(amount="12", transaction_date="2026-10-10")

    result = get_expense_by_category("2026-10")

    assert [(i["category"], i["total"]) for i in result] == [
        ("Alimentación", 12.0),
    ]


def test_month_without_expenses_returns_empty_list(client):
    assert get_expense_by_category("2026-10") == []


def test_percentages_add_up_to_100(client, add_transaction):
    add_transaction(amount="7", category="Alimentación")
    add_transaction(amount="11", category="Transporte")
    add_transaction(amount="3", category="Salud")

    result = get_expense_by_category("2026-10")

    assert sum(i["percent"] for i in result) == pytest.approx(100)


def test_dashboard_loads_with_chart_month(client, add_transaction):
    add_transaction(transaction_date="2026-10-02")

    assert client.get("/?month=2026-10").status_code == 200


def test_dashboard_ignores_invalid_month(client):
    assert client.get("/?month=abc").status_code == 200