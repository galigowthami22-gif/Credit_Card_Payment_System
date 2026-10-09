import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

PaymentStatus = Literal["PENDING", "SUCCESS", "FAILED"]


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path) -> None:
    with closing(_connect(database_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount TEXT NOT NULL,
                    card_last_four TEXT NOT NULL CHECK (length(card_last_four) = 4),
                    status TEXT NOT NULL
                        CHECK (status IN ('PENDING', 'SUCCESS', 'FAILED')),
                    failure_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )


def create_pending_payment(
    database_path: Path,
    amount: Decimal,
    card_last_four: str,
) -> int:
    now = datetime.now(UTC).isoformat()
    with closing(_connect(database_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO payments (
                    amount, card_last_four, status, created_at, updated_at
                )
                VALUES (?, ?, 'PENDING', ?, ?)
                """,
                (format(amount, ".2f"), card_last_four, now, now),
            )
            return cursor.lastrowid


def finalize_payment(
    database_path: Path,
    payment_id: int,
    status: Literal["SUCCESS", "FAILED"],
    failure_reason: str | None = None,
) -> None:
    with closing(_connect(database_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                UPDATE payments
                SET status = ?, failure_reason = ?, updated_at = ?
                WHERE id = ? AND status = 'PENDING'
                """,
                (status, failure_reason, datetime.now(UTC).isoformat(), payment_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(f"Pending payment {payment_id} could not be finalized.")


def get_payment(database_path: Path, payment_id: int) -> sqlite3.Row | None:
    with closing(_connect(database_path)) as connection:
        return connection.execute(
            "SELECT * FROM payments WHERE id = ?",
            (payment_id,),
        ).fetchone()
