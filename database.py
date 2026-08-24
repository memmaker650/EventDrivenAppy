import sqlite3
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DB_NAME = "events.db"

def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    logger.info("init_DB")
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
    CREATE TABLE IF NOT EXISTS accounts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at DATE DEFAULT (datetime('now')),
        state TEXT NOT NULL,
        money REAL NOT NULL DEFAULT 0.0
    )
    """)

    conn.commit()
    conn.close() 

def load_accountInfo(cuenta):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT account_id,
            titular,
            saldo,
            estado,
            ultimo_movimiento
        FROM account
        where account_id = ?
    """,            
    (
        cuenta,
    ),)

    datos = cursor.fetchall() 

def crearCuenta(accid, owner):
    conn = get_connection()

    fechaActual = datetime.now()

    conn.execute(
        """
        INSERT INTO accounts(
        account_id,
        name,
        created_at,
        state,
        money
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            accid.value,
            owner.value,
            fechaActual, 
            "open",
            0.0,
        ),
    )

    conn.commit()
    conn.close()

def update_accountMoney(dinero, cuenta):
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE accounts SET 
        money = ?
        where account_id = ?
    """,            
    (
        dinero, cuenta,
    ),)

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
    logger.info("Dentro de Guardado un Evento.")
    try:    
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
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
                datetime.now(),
            ),
        )

        conn.commit()
        logger.info("Insert realizado correctamente")
        return {
            "ok": True,
            "id": cur.lastrowid,
            "mensaje": "Evento insertado"
        }
    except sqlite3.Error as e:
        logger.error(f"Error al insertar: {e}")
        return {
            "ok": False,
            "id": None,
            "mensaje": str(e)
        }
    finally:
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
    logger.info("load_accounts")
    conn = get_connection()

    cur = conn.execute("""
        SELECT DISTINCT aggregate_id
        FROM event_store
        ORDER BY aggregate_id
    """)

    cuentas = [row[0] for row in cur.fetchall()]

    conn.close()

    return cuentas

def check_num_accounts_user():
    logger.info("check_num_accounts_user")
    conn = get_connection()

    cuentas = conn.execute("""
        SELECT owner, COUNT(*) AS num_cuentas
        FROM account
        GROUP BY owner
        ORDER BY owner asc;
    """).fetchall()

    conn.close()

    for owner, num_cuentas in cuentas:
        print(f"{owner}: {num_cuentas}")

    return cuentas

# Complejo, deben ser cuentas idénticas, con mismos movimientos.
def check_dup_accounts():
    logger.info("check_dup_accounts")
    conn = get_connection()

    cur = conn.execute("""
        SELECT DISTINCT aggregate_id
        FROM event_store
        ORDER BY aggregate_id
    """)

    cuentas = [row[0] for row in cur.fetchall()]

    conn.close()

    return cuentas

def check_overdraft():
    logger.info("check_overdraft")

    conn = get_connection()

    cuentas = conn.execute("""
        SELECT account, money
        FROM account
        ORDER BY money asc
    """)

    conn.close()

    for cuenta in cuentas:        
        money = cuenta[1]
        if money < 0:
            print("Cuenta: "+cuenta[1]+"Saldo: " +money)
            logger.info("Cuenta: "+cuenta[1]+"Saldo: " +money)

    return cuentas