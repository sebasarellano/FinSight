"""Pruebas de la página de resumen (dashboard)."""

import re


def test_new_movement_button_links_to_movements_page(client):
    html = client.get("/").get_data(as_text=True)

    # Debe ser un enlace real a la página donde se registran los movimientos.
    assert re.search(
        r'<a class="button button-primary" href="/transactions">', html
    )
    assert "Nuevo movimiento" in html


def test_stale_disabled_button_is_gone(client):
    html = client.get("/").get_data(as_text=True)

    assert "disabled" not in html
    assert "Disponible cuando implementemos" not in html
