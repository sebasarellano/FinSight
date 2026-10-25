"""Pruebas de la exportación de movimientos a CSV."""

import csv
import io


def add_transaction(client, **changes):
    """Registra un movimiento válido; cada prueba cambia solo lo suyo."""
    form = {
        "description": "Almuerzo de prueba",
        "amount": "10.50",
        "transaction_type": "expense",
        "category": "Alimentación",
        "transaction_date": "2026-10-24",
        "account_id": "1",
    }
    form.update(changes)
    client.post("/transactions", data=form)


def read_csv(response):
    """Convierte la respuesta en una lista de filas."""
    text = response.data.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def test_export_headers_and_download_name(client):
    response = client.get("/transactions/export.csv")

    assert response.status_code == 200
    assert response.content_type.startswith("text/csv")
    disposition = response.headers["Content-Disposition"]
    assert "attachment" in disposition
    assert ".csv" in disposition


def test_export_without_data_has_only_header(client):
    rows = read_csv(client.get("/transactions/export.csv"))

    assert rows == [
        ["fecha", "descripcion", "tipo", "categoria", "cuenta", "importe"]
    ]


def test_export_contains_saved_transaction(client):
    add_transaction(client)

    rows = read_csv(client.get("/transactions/export.csv"))

    assert rows[1] == [
        "2026-10-24",
        "Almuerzo de prueba",
        "gasto",
        "Alimentación",
        "Efectivo",
        "10.50",
    ]


def test_export_amount_has_two_decimals(client):
    add_transaction(client, amount="10")

    rows = read_csv(client.get("/transactions/export.csv"))

    assert rows[1][5] == "10.00"


def test_export_keeps_commas_and_quotes(client):
    description = 'Pan, leche y "queso"'
    add_transaction(client, description=description)

    rows = read_csv(client.get("/transactions/export.csv"))

    assert rows[1][1] == description


def test_export_neutralizes_formulas(client):
    add_transaction(client, description="=1+1")

    rows = read_csv(client.get("/transactions/export.csv"))

    assert rows[1][1] == "'=1+1"


def test_export_starts_with_bom_for_excel(client):
    response = client.get("/transactions/export.csv")

    assert response.data.startswith(b"\xef\xbb\xbf")