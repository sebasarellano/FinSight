"""Preparación común de las pruebas de FinSight."""

import pytest

import database
from app import app as flask_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Cliente de pruebas con una base de datos temporal y vacía.

    monkeypatch cambia la ruta de la base de datos solo durante la
    prueba: al terminar, todo vuelve a su valor original. Así las
    pruebas nunca tocan instance/finsight.db.
    """
    monkeypatch.setattr(database, "DATABASE_FOLDER", tmp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "test.db")

    # Crea las tablas y las 3 cuentas de ejemplo en la base temporal.
    database.initialize_database()

    flask_app.config.update(TESTING=True)

    with flask_app.test_client() as test_client:
        yield test_client


@pytest.fixture
def add_transaction(client):
    """Devuelve una función que registra un movimiento válido.

    Cada prueba indica solo los campos que quiere cambiar.
    """

    def _add(**changes):
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

    return _add
