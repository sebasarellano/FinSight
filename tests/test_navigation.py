"""Pruebas de la estructura común de las páginas (barra lateral y accesibilidad)."""

import pytest


def test_skip_link_points_to_main_content(client):
    html = client.get("/").get_data(as_text=True)

    # El enlace y su destino deben existir a la vez, o el enlace no sirve.
    assert 'href="#contenido"' in html
    assert 'id="contenido"' in html


@pytest.mark.parametrize(
    "url, label",
    [
        ("/", "Resumen"),
        ("/transactions", "Movimientos"),
        ("/budgets", "Presupuestos"),
        ("/accounts", "Cuentas"),
    ],
)
def test_current_section_is_marked_in_navigation(client, url, label):
    html = client.get(url).get_data(as_text=True)

    # Solo una sección puede estar marcada como la página actual.
    assert html.count('aria-current="page"') == 1
    assert f'<span class="nav-label">{label}</span>' in html


def test_stale_labels_are_gone(client):
    html = client.get("/").get_data(as_text=True)

    assert "VERSIÓN INICIAL" not in html
    assert "Modo demostración" not in html
