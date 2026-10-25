"""Pruebas de los presupuestos: guardar, actualizar y eliminar."""

import database


def budget_form(**changes):
    """Formulario válido de presupuesto; cada prueba cambia solo lo suyo."""
    form = {
        "category": "Alimentación",
        "month": "2026-10",
        "amount": "200",
    }
    form.update(changes)
    return form


def get_budgets():
    """Devuelve todos los presupuestos de la base temporal."""
    connection = database.get_db_connection()

    try:
        return connection.execute(
            "SELECT id, category, month, amount FROM budgets"
        ).fetchall()
    finally:
        connection.close()


def test_budget_is_saved(client):
    client.post("/budgets", data=budget_form())

    assert len(get_budgets()) == 1


def test_same_category_and_month_updates_amount(client):
    client.post("/budgets", data=budget_form(amount="200"))
    client.post("/budgets", data=budget_form(amount="300"))

    budgets = get_budgets()

    # No se duplica: se actualiza el importe del existente.
    assert len(budgets) == 1
    assert budgets[0]["amount"] == 300


def test_income_category_cannot_be_budgeted(client):
    client.post("/budgets", data=budget_form(category="Salario"))

    assert get_budgets() == []


def test_budget_is_deleted(client):
    client.post("/budgets", data=budget_form())
    budget_id = get_budgets()[0]["id"]

    response = client.post(f"/budgets/{budget_id}/delete")

    assert response.status_code == 302
    assert get_budgets() == []


def test_deleting_missing_budget_does_not_fail(client):
    response = client.post("/budgets/999/delete")

    # Redirige con un aviso en lugar de romperse.
    assert response.status_code == 302


def test_delete_budget_rejects_get(client):
    # Una acción que modifica datos solo debe aceptar POST.
    response = client.get("/budgets/1/delete")

    assert response.status_code == 405