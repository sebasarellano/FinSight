import sqlite3
from pathlib import Path


# Ruta de la carpeta y del archivo de la base de datos.
PROJECT_FOLDER = Path(__file__).resolve().parent
DATABASE_FOLDER = PROJECT_FOLDER / "instance"
DATABASE_PATH = DATABASE_FOLDER / "finsight.db"


def get_db_connection():
    """Abre una conexión con la base de datos SQLite."""
    DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Crea las tablas y las cuentas de ejemplo si aún no existen."""
    with get_db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL
                    CHECK (
                        account_type IN (
                            'cash',
                            'bank',
                            'savings',
                            'other'
                        )
                    ),
                -- Puede ser negativo: representa una cuenta que empieza
                -- con deuda (por ejemplo, una tarjeta de crédito).
                initial_balance REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                transaction_type TEXT NOT NULL
                    CHECK (
                        transaction_type IN (
                            'income',
                            'expense',
                            'transfer'
                        )
                    ),
                category TEXT NOT NULL,
                transaction_date TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                destination_account_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (account_id)
                    REFERENCES accounts(id)
                    ON DELETE RESTRICT,

                FOREIGN KEY (destination_account_id)
                    REFERENCES accounts(id)
                    ON DELETE RESTRICT,

                CHECK (
                    (
                        transaction_type = 'transfer'
                        AND destination_account_id IS NOT NULL
                        AND destination_account_id != account_id
                    )
                    OR
                    (
                        transaction_type != 'transfer'
                        AND destination_account_id IS NULL
                    )
                )
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_date
            ON transactions(transaction_date);

            CREATE INDEX IF NOT EXISTS idx_transactions_account
            ON transactions(account_id);
            """
        )

        # Crear las cuentas de ejemplo solo la primera vez.
        account_count = connection.execute(
            "SELECT COUNT(*) FROM accounts"
        ).fetchone()[0]

        if account_count == 0:
            example_accounts = [
                ("Efectivo", "cash", 325.50),
                ("Cuenta bancaria", "bank", 2100.00),
                ("Ahorros", "savings", 6000.00),
            ]

            connection.executemany(
                """
                INSERT INTO accounts (
                    name,
                    account_type,
                    initial_balance
                )
                VALUES (?, ?, ?)
                """,
                example_accounts,
            )


if __name__ == "__main__":
    initialize_database()
    print("Base de datos inicializada correctamente.")
    print(f"Ubicación: {DATABASE_PATH}")