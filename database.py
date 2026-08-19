import sqlite3
import json
from datetime import datetime

DB_NAME = "events.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS event_store(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aggregate_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_data TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def save_event(aggregate_id, event_type, event_data):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO event_store(
            aggregate_id,
            event_type,
            event_data,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            aggregate_id,
            event_type,
            json.dumps(event_data),
            datetime.utcnow().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def load_events(aggregate_id):
    conn = get_connection()

    cur = conn.execute(
        """
        SELECT event_type, event_data
        FROM event_store
        WHERE aggregate_id = ?
        ORDER BY id
        """,
        (aggregate_id,),
    )

    rows = cur.fetchall()
    conn.close()

    return rows

def loadMaxAccountID():
    conn = get_connection()

    cur = conn.execute(
        """
        SELECT MAX(CAST(SUBSTR(aggregate_id,5) AS INTEGER))
        FROM event_store
        """,
    )

    maximo = cur.fetchone()[0]
    conn.close()

    return maximo   