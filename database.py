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

# Buscar info sobre una cuenta.
def load_accountInfo(cuenta):
    conn = get_connection()
    cursor = conn.cursor()

    print("cuenta Buscar: ", cuenta)

    cursor.execute("""
        SELECT account_id,
               name,
               money,
               state,
               created_at
        FROM accounts
        WHERE account_id = ?
    """, 
    (cuenta,))

    datos = cursor.fetchone()
    print("Cuenta Info Obtenida: ", datos)

    conn.close()

    return datos

# Método para crear cuenta en la tabla ACCOUTS
def crearCuenta(accid, owner):
    conn = get_connection()

    fechaActual = datetime.now()
    print("accidDB:", accid)

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
            accid,
            owner,
            fechaActual, 
            "open",
            0.0,
        ),
    )

    conn.commit()
    conn.close()

def load_accountMoney(dinero, cuenta):
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

    conn.close()      

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

# Cargar los eventos de un id de una cuenta.
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
    print("Eventos:  ", rows)
    conn.close()

    return rows

# Cargar los eventos de un id de una cuenta.
def load_eventsFull(aggregate_id):
    conn = get_connection()

    cur = conn.execute(
        """
        SELECT aggregate_id, event_type, event_data, created_at
        FROM event_store
        WHERE aggregate_id = ?
        ORDER BY id
        """,
        (aggregate_id,),
    )

    rows = cur.fetchall()
    print("Eventos:  ", rows)
    conn.close()

    return rows

# Cargar los eventos de un id de una cuenta.
def load_diffIDAccountInEvents():
    conn = get_connection()

    cur = conn.execute(
        """
        SELECT DISTINCT(aggregate_id)
        FROM event_store
        ORDER BY id asc
        """,
    )

    rows = cur.fetchall()
    conn.close()

    return rows

# Cargar los eventos de un id de una cuenta.
def load_ownerForAccountInEvent(cuenta):
    conn = get_connection()

    print("DB cuenta: ", cuenta)
    cur = conn.execute("""
        SELECT json_extract(event_data, '$.owner')
        FROM event_store
        WHERE aggregate_id = ?  
        AND event_type = "AccountCreated"
        """, (cuenta,))

    owner = cur.fetchone()
    print("DB Duegno: ", owner)
    conn.close()

    return owner[0] if owner else None

# Retornar los eventos de un id de una cuenta, no AccountCreated
def load_moneyForAccountInEvent(cuenta):
    conn = get_connection()

    cuenta = cuenta[0]

    print("DB cuenta: ", cuenta)
    cur = conn.execute("""
        SELECT event_type, json_extract(event_data, '$.amount')
        FROM event_store
        WHERE aggregate_id = ?  
        AND event_type NOT IN ("AccountCreated", "CloseAccount")
        """, (cuenta,))

    money = cur.fetchall()
    print("DB montante: ", money)
    conn.close()

    return money if money else None 

# Cargar los eventos de un id de una cuenta.
def store_moneyForAccount(dinero, cuenta):
    conn = get_connection()

    cuenta = cuenta[0]

    print("DB cuenta: ", cuenta)
    cur = conn.execute("""
        UPDATE accounts
        SET money = ?
        WHERE account_id = ?  
        """, (dinero, cuenta,))

    conn.commit()

    print("Filas actualizadas:", cur.rowcount)

    conn.close()         

    return cur.rowcount 

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