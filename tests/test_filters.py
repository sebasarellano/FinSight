"""Pruebas de filtros, búsqueda y ordenamiento de movimientos."""

import pytest

from app import get_transactions, parse_transaction_filters


@pytest.fixture
def sample_data(add_transaction):
    """Cuatro movimientos con fechas, categorías y cuentas distintas."""
    add_transaction(
        description="Pan y leche", amount="12.00",
        category="Alimentación", transaction_date="2026-10-02",
    )
    add_transaction(
        description="Bus al trabajo", amount="3.50",
        category="Transporte", transaction_date="2026-10-05",
    )
    add_transaction(
        description="Sueldo octubre", amount="900",
        transaction_type="income", category="Salario",
        transaction_date="2026-10-01",
    )
    add_transaction(
        description="Cena fuera", amount="25",
        category="Alimentación", transaction_date="2026-09-20",
        account_id="2",
    )


def descriptions(args):
    """Descripciones devueltas con esos filtros, en orden."""
    filters = parse_transaction_filters(args)
    return [t["description"] for t in get_transactions(filters=filters)]


DEFAULT_ORDER = [
    "Bus al trabajo", "Pan y leche", "Sueldo octubre", "Cena fuera",
]


def test_default_order_is_newest_first(sample_data):
    assert descriptions({}) == DEFAULT_ORDER


def test_search_ignores_case(sample_data):
    assert descriptions({"q": "PAN"}) == ["Pan y leche"]


def test_search_treats_percent_as_text(sample_data, add_transaction):
    add_transaction(description="Descuento 100% real")

    # Si % fuera un comodín, devolvería todos los movimientos.
    assert descriptions({"q": "%"}) == ["Descuento 100% real"]


def test_filter_by_type(sample_data):
    assert descriptions({"type": "income"}) == ["Sueldo octubre"]


def test_filter_by_category(sample_data):
    assert descriptions({"category": "Alimentación"}) == [
        "Pan y leche", "Cena fuera",
    ]


def test_filter_by_account(sample_data):
    assert descriptions({"account": "2"}) == ["Cena fuera"]


def test_filter_by_date_range_is_inclusive(sample_data):
    args = {"date_from": "2026-10-02", "date_to": "2026-10-05"}

    assert descriptions(args) == ["Bus al trabajo", "Pan y leche"]


def test_filters_combine(sample_data):
    args = {"category": "Alimentación", "date_from": "2026-10-01"}

    assert descriptions(args) == ["Pan y leche"]


def test_sort_by_amount_ascending(sample_data):
    args = {"sort": "amount", "order": "asc"}

    assert descriptions(args) == [
        "Bus al trabajo", "Pan y leche", "Cena fuera", "Sueldo octubre",
    ]


def test_sort_by_description_ignores_case(sample_data):
    args = {"sort": "description", "order": "asc"}

    assert descriptions(args) == [
        "Bus al trabajo", "Cena fuera", "Pan y leche", "Sueldo octubre",
    ]


def test_invalid_values_are_ignored(sample_data):
    args = {
        "type": "transfer",
        "category": "Inexistente",
        "account": "9" * 30,
        "date_from": "2026-13-45",
        "sort": "id; DROP TABLE transactions",
        "order": "sideways",
    }

    filters = parse_transaction_filters(args)

    assert filters["sort"] == "date"
    assert filters["order"] == "desc"
    assert descriptions(args) == DEFAULT_ORDER


def test_page_applies_filters(client, sample_data):
    response = client.get("/transactions?q=pan&sort=amount&order=asc")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Pan y leche" in html
    assert "Bus al trabajo" not in html


def test_page_shows_message_when_nothing_matches(client, sample_data):
    html = client.get("/transactions?q=zzzz").get_data(as_text=True)

    assert "Ningún movimiento coincide" in html


def test_export_respects_filters(client, sample_data):
    response = client.get("/transactions/export.csv?type=income")
    lines = response.data.decode("utf-8-sig").strip().splitlines()

    # Encabezado + el único ingreso.
    assert len(lines) == 2
    assert "Sueldo octubre" in lines[1]