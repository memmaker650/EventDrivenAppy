import sqlite3
import json
from datetime import datetime

DB_NAME = "events.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    create_eventsTable()
    create_AccountTable()
    create_Account_states()

def create_eventsTable():
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

def create_AccountTable():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS account_name(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aggregate_id TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        state TEXT NOT NULL,
        money REAL NOT NULL DEFAULT 0.0
    )
    """)

    conn.commit()
    conn.close() 

def load_accountInfo():
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id_cuenta,
            titular,
            saldo,
            estado,
            ultimo_movimiento
        FROM cuentas
    """)

    datos = cursor.fetchall()    

def create_Account_states():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS acc_state_names(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        state TEXT NOT NULL,
        name TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

    fill_account_states() 

def check_state_names():
    conn = get_connection()

    cur = conn.execute(
        """
        SELECT COUNT(*)
        FROM acc_state_names
        """,
    )

    c = cur.fetchone()[0]
    conn.close()

    print("COUNT: ",c)

    return c  

def fill_account_states():
    if check_state_names() > 0:
        flag = False
    else:
        flag = True

    if flag:    
        conn = get_connection()

        conn.execute(
            """
            INSERT INTO acc_state_names(
                id,
                state,
                name
            )
            VALUES (?, ?, ?)
            """,
            (
                1,
                "blocked",
                "Bloqueado"
            ),
        )

        conn.execute(
            """
            INSERT INTO acc_state_names(
                id,
                state,
                name
            )
            VALUES (?, ?, ?)
            """,
            (
                2,
                "active",
                "Activo"
            ),
        )

        conn.execute(
            """
            INSERT INTO acc_state_names(
                id,
                state,
                name
            )
            VALUES (?, ?, ?)
            """,
            (
                3,
                "closed",
                "Cerrado"
            ),
        )

        conn.execute(
            """
            INSERT INTO acc_state_names(
                id,
                state,
                name
            )
            VALUES (?, ?, ?)
            """,
            (
                4,
                "alert",
                "Alerta"
            ),
        )

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

def load_accounts():

    conn = get_connection()

    cur = conn.execute("""
        SELECT DISTINCT aggregate_id
        FROM event_store
        ORDER BY aggregate_id
    """)

    cuentas = [row[0] for row in cur.fetchall()]

    conn.close()

    return cuentas