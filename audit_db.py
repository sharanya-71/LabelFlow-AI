
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "labelflow_audit.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                filename TEXT,
                details TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def record_event(action, filename=None, details=None):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_history (action, filename, details)
            VALUES (?, ?, ?)
            """,
            (action, filename, details),
        )
        return cursor.lastrowid


def get_history(limit=100):
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, action, filename, details, created_at
            FROM audit_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


initialize_database()
