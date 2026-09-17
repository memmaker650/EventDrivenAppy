import sys
import sqlite3
import json
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_NAME = "events.db"

def get_connection():
    if sys.platform == "win32":
        db_file = Path(r"C:\Users\Jorge.Vega\Documents\ENABLON-proj\PROYECTOS\EbD\EventDrivenApplication\db")
    elif sys.platform == "darwin":
        db_file = Path.home() / "PycharmProjects" / "EventDrivenAppy" / "db"
    else:
        db_file = Path.home() / "EventDrivenApplication" / "db"
    
    db_file.mkdir(parents=True, exist_ok=True)   # crea la carpeta si no existe

    db_file = db_file / DB_NAME                  # 👈 aquí concatenas carpeta + nombre

    return sqlite3.connect(db_file)

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

def _as_id(cuenta):
    if isinstance(cuenta, (tuple, list)):
        return cuenta[0]
    return cuenta


# Buscar info sobre una cuenta.
def load_accountInfo(cuenta):
    conn = get_connection()
    cursor = conn.cursor()
    cuenta = _as_id(cuenta)

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
    try:
        conn = get_connection()

        fechaActual = datetime.now().isoformat()
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
        return True
    except sqlite3.Error as e:
        print(f"Error al insertar: {e}")
        return False
    finally:
        conn.close()

def load_accountMoney(dinero, cuenta):
    conn = get_connection()
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
                datetime.now().isoformat(timespec='seconds'),
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
    # print("Eventos:  ", rows)
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
    # print("Eventos:  ", rows)
    conn.close()

    return rows

# Cargar los eventos de un id de una cuenta.
def load_eventsOfType(aggregate_id, type):
    conn = get_connection()

    cur = conn.execute(
        """
        SELECT aggregate_id, event_type, event_data, created_at
        FROM event_store
        WHERE aggregate_id = ?
        AND event_type = ?
        ORDER BY id
        """,
        (aggregate_id, type),
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

    cuenta = _as_id(cuenta)

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

    cuenta = _as_id(cuenta)

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

    if maximo == None:
        maximo = 0

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
        SELECT name, COUNT(*) AS num_cuentas
        FROM accounts
        GROUP BY name
        ORDER BY name asc;
    """).fetchall()

    conn.close()

    for owner, num_cuentas in cuentas:
        print(f"{owner}: {num_cuentas}")

    return cuentas

def return_MoneyTransfer():
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

# Complejo, deben ser cuentas idénticas, con mismos movimientos.
def check_dup_accounts():
    logger.info("check_dup_accounts")
    conn = get_connection()

    cur = conn.execute("""
        SELECT *
        FROM event_store
        WHERE event_type = "MoneyTransfer"
        ORDER BY aggregate_id
    """)

    cuentas = [row[0] for row in cur.fetchall()]

    conn.close()

    return cuentas

def check_overdraft():
    logger.info("check_overdraft")

    conn = get_connection()

    cuentas = conn.execute("""
        SELECT account_id, money
        FROM accounts
        ORDER BY money asc
    """).fetchall()

    conn.close()

    for cuenta in cuentas:
        money = cuenta[1]
        if money < 0:
            print("Cuenta: " + str(cuenta[0]) + " Saldo: " + str(money))
            logger.info("Cuenta: " + str(cuenta[0]) + " Saldo: " + str(money))

    return cuentas

# Parte de Hypotekas 
#----------------------------
def create_hipotecasTable():
    logger.info("Creando Tabla Hipotecas")

    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS hipotecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_asociada TEXT NOT NULL,
        hipoteca_id TEXT NOT NULL,
        capital_inicial REAL NOT NULL,
        tasa_anual REAL NOT NULL,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        cuota_mensual REAL NOT NULL,
        meses_totales INTEGER NOT NULL,
        meses_restantes INTEGER NOT NULL,
        saldo_actual REAL NOT NULL,
        es_Credito BOOLEAN NOT NULL default 0,
        FOREIGN KEY (cuenta_asociada) REFERENCES accounts(account_id)
    )""")

    conn.commit()
    conn.close()

def create_amortizaciones_anticipadasTable():
    logger.info("Creando Tabla amortizaciones Anticipadas")

    conn = get_connection()

    conn.execute("""CREATE TABLE IF NOT EXISTS amortizaciones_anticipadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hipoteca_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    importe REAL NOT NULL,
    comision REAL NOT NULL,
    FOREIGN KEY (hipoteca_id) REFERENCES hipotecas(id)
    )""")

    conn.commit()
    conn.close()

def generar_id_hypoteka():
    logger.info("Generar ID Hipoteca")

    conn = get_connection()

    cur = conn.execute("""
        SELECT hipoteca_id
        FROM hipotecas
        ORDER BY id DESC
        LIMIT 1
        """)

    ultimo = cur.fetchone()
    print("Hypoteka_id: ", ultimo)

    if not ultimo:
        return "HYP-001"

    numero = int(ultimo[0].split("-")[1]) + 1

    return f"HYP-{numero:03d}"

def generar_id_credito():
    logger.info("Generar id Crédito")

    conn = get_connection()

    cur = conn.execute("""
        SELECT hipoteca_id
        FROM hipotecas
        WHERE es_Credito = 1
        ORDER BY id DESC
        LIMIT 1
        """)

    ultimo = cur.fetchone()
    print("Crédito_id: ", ultimo)

    if not ultimo:
        return "CRE-001"

    numero = int(ultimo[0].split("-")[1]) + 1

    return f"CRE-{numero:03d}"

def cargar_nuevaHypoteka(origen, hipoteca_id, capital, tasa_anual, fecha_inicio, fecha_fin, cuota, meses, credito=0):
    logger.info("Insertar Nueva Hipoteca")

    fecha_inicio = fecha_inicio.date().isoformat()
    fecha_fin = fecha_fin.date().isoformat()
    # Cálculo meses restantes
    meses_restante = meses
    saldo_actual = capital

    conn = get_connection()

    if credito !=0:
            conn.execute("""
            INSERT INTO hipotecas(cuenta_asociada, hipoteca_id, capital_inicial, tasa_anual, fecha_inicio, fecha_fin, cuota_mensual, meses_totales, meses_restantes, saldo_actual, es_Credito)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                origen,
                hipoteca_id,
                capital,
                tasa_anual,
                fecha_inicio,
                fecha_fin,
                cuota, 
                meses_restante,
                meses_restante,
                saldo_actual,
                1
            ))
    else:   
        conn.execute("""
            INSERT INTO hipotecas(cuenta_asociada, hipoteca_id, capital_inicial, tasa_anual, fecha_inicio, fecha_fin, cuota_mensual, meses_totales, meses_restantes, saldo_actual)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                origen,
                hipoteca_id,
                capital,
                tasa_anual,
                fecha_inicio,
                fecha_fin,
                cuota, 
                meses_restante,
                meses_restante,
                saldo_actual
            ))

    conn.commit()

def buscar_hypoteka(hipoteca_id):
    logger.info("SELECT Hipoteca por ID")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT saldo_actual,
                cuota_mensual,
                tasa_anual
            FROM hipotecas
            WHERE id = ?
        """, (hipoteca_id,))

    fila = cursor.fetchone()

    return fila

def guardar_amortizacion(hipoteca_id, fecha, importe):
    logger.info("INSERT Amortización Anticipada")

    comision = round(importe * 0.005, 2)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO amortizaciones_anticipadas
        (
            hipoteca_id,
            fecha,
            importe,
            comision
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            hipoteca_id,
            fecha,
            importe,
            comision
        ))

    conn.commit()

    return comision

def actualizar_hypotekaAmortizacion(resultado, hipoteca_id, importe_amortizado):
    logger.info("UPDATE actualizar hypoteka Amortizacion")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            UPDATE hipotecas
            SET saldo_actual = ?,
                meses_restantes = ?
            WHERE id = ?
        """,
        (
            resultado["nuevo_saldo"],
            resultado["meses_restantes"],
            hipoteca_id
        ))

    cursor.execute("""
            INSERT INTO amortizaciones_anticipadas(
                hipoteca_id,
                fecha,
                importe,
                comision
            )
            VALUES(
                ?, date('now'), ?, ?
            )
        """,
        (
            hipoteca_id,
            importe_amortizado,
            resultado["comision"]
        ))

    conn.commit()

def buscar_hypoteka_asociadaCuenta(cuenta_asociada):
    logger.info("BUSCAR Hypoteka a partir de cuenta.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT hipoteca_id
            FROM hipotecas
            WHERE cuenta_asociada = ?
        """,
        (
            cuenta_asociada,
        ))

    fila = cursor.fetchone()

    return fila

def buscar_credito_asociadaCuenta(cuenta_asociada):
    logger.info("BUSCAR Crédito a partir de cuenta.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
            SELECT hipoteca_id
            FROM hipotecas
            WHERE cuenta_asociada = ?
            AND es_Credito = 1
        """,
        (
            cuenta_asociada,
        ))

    fila = cursor.fetchone()

    return fila    

def listar_hypotecasCreditos_asociados(account_asociada, tipo):
    logger.info("Listar Crédito a partir de cuenta.")

    conn = get_connection()
    cursor = conn.cursor()

    print("Cuenta Linked:", account_asociada, " Tipo: ", tipo)

    if tipo == 0:
        cursor.execute("""
                SELECT hipoteca_id
                FROM hipotecas
                WHERE cuenta_asociada = ?
                AND es_Credito = 0
            """,
            (
                account_asociada,
            ))
    else:
        cursor.execute("""
                SELECT hipoteca_id
                FROM hipotecas
                WHERE cuenta_asociada = ?
                AND es_Credito = 1
            """,
            (
                account_asociada,
            ))

    fila = cursor.fetchall()
    print("Return Hypo/Creds Linked: ", fila)

    return fila 

def listar_hypotecasCreditos_General(tipo):
    logger.info("Listar Crédito a partir de cuenta.")

    conn = get_connection()
    cursor = conn.cursor()

    if tipo == 0:
        cursor.execute("""
                SELECT hipoteca_id
                FROM hipotecas
                WHERE es_Credito = 0
            """)
    else:
        cursor.execute("""
                SELECT hipoteca_id
                FROM hipotecas
                WHERE es_Credito = 1
            """
            )

    fila = cursor.fetchone()

    return fila

def obtenerInfoCreditoHypoteka(hypcre_id):   
    logger.info("Obtener detalles del Crédito Hipoteca.")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cuenta_asociada, hipoteca_id, capital_inicial, tasa_anual, fecha_inicio, cuota_mensual, meses_totales, saldo_actual
        FROM hipotecas
        WHERE hipoteca_id = ?
        """,
        (
            hypcre_id,
        ))

    fila = cursor.fetchone()
    print("DB Details hypo/Cred: ", fila)

    return fila