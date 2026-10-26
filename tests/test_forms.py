"""Los límites de los formularios deben coincidir con los del servidor.

Si el servidor rechaza un importe pero el campo lo acepta, la persona solo
se entera al enviar. Estas pruebas atan el atributo HTML a la constante.
"""

from app import (
    MAX_BUDGET_AMOUNT,
    MAX_INITIAL_BALANCE,
    MAX_TRANSACTION_AMOUNT,
)


def test_transaction_form_max_matches_server_limit(client):
    html = client.get("/transactions").get_data(as_text=True)

    assert f'max="{MAX_TRANSACTION_AMOUNT}"' in html


def test_edit_transaction_form_max_matches_server_limit(client, add_transaction):
    add_transaction()

    html = client.get("/transactions/1/edit").get_data(as_text=True)

    assert f'max="{MAX_TRANSACTION_AMOUNT}"' in html


def test_budget_form_max_matches_server_limit(client):
    html = client.get("/budgets").get_data(as_text=True)

    assert f'max="{MAX_BUDGET_AMOUNT}"' in html


def test_edit_account_form_limits_match_server(client):
    html = client.get("/accounts/1/edit").get_data(as_text=True)

    # El saldo inicial admite negativos (deudas), con el mismo tope.
    assert f'max="{MAX_INITIAL_BALANCE}"' in html
    assert f'min="-{MAX_INITIAL_BALANCE}"' in html
