from datetime import datetime

import sqlite3

import database


def test_init_db_crea_tablas(isolated_db):
    conn = database.get_connection()
    tablas = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()
    assert "event_store" in tablas
    assert "accounts" in tablas
    assert "acc_state_names" in tablas
    assert "hipotecas" in tablas
    assert "amortizaciones_anticipadas" in tablas


def test_fill_account_states_no_duplica(isolated_db):
    database.fill_account_states()
    assert database.check_state_names() == 4


def test_crear_cuenta_y_load_account_info(isolated_db):
    assert database.crearCuenta("ACC-001", "Ana") is True
    info = database.load_accountInfo("ACC-001")
    assert info[0] == "ACC-001"
    assert info[1] == "Ana"
    assert info[2] == 0.0
    assert info[3] == "open"


def test_crear_cuenta_error_sql(isolated_db, monkeypatch):
    class FakeConn:
        def execute(self, *args, **kwargs):
            raise sqlite3.Error("fallo insert")

        def close(self):
            return None

    monkeypatch.setattr(database, "get_connection", lambda: FakeConn())
    assert database.crearCuenta("ACC-ERR", "X") is False


def test_save_and_load_events(isolated_db):
    resultado = database.save_event("ACC-002", "AccountCreated", {"owner": "Luis"})
    assert resultado["ok"] is True
    assert resultado["id"] == 1

    eventos = database.load_events("ACC-002")
    assert eventos[0][0] == "AccountCreated"

    full = database.load_eventsFull("ACC-002")
    assert full[0][0] == "ACC-002"
    assert full[0][1] == "AccountCreated"

    typed = database.load_eventsOfType("ACC-002", "AccountCreated")
    assert len(typed) == 1


def test_save_event_error(isolated_db, monkeypatch):
    class FakeConn:
        def cursor(self):
            raise sqlite3.Error("sin cursor")

        def close(self):
            return None

    monkeypatch.setattr(database, "get_connection", lambda: FakeConn())
    resultado = database.save_event("ACC-X", "X", {})
    assert resultado["ok"] is False
    assert resultado["id"] is None


def test_load_accounts_y_max_id(isolated_db):
    database.save_event("ACC-003", "AccountCreated", {"owner": "Eva"})
    database.save_event("ACC-010", "AccountCreated", {"owner": "Paco"})

    cuentas = database.load_accounts()
    assert cuentas == ["ACC-003", "ACC-010"]
    assert database.loadMaxAccountID() == 10
    assert database.load_diffIDAccountInEvents() == [("ACC-003",), ("ACC-010",)]


def test_load_max_account_id_vacio(isolated_db):
    assert database.loadMaxAccountID() == 0


def test_owner_y_money_desde_eventos(isolated_db):
    database.save_event("ACC-004", "AccountCreated", {"owner": "Nuria"})
    database.save_event("ACC-004", "MoneyDeposited", {"amount": 100})
    database.save_event("ACC-004", "Moneywithdraw", {"amount": 30})

    assert database.load_ownerForAccountInEvent("ACC-004") == "Nuria"
    assert database.load_ownerForAccountInEvent("NO-EXISTE") is None

    money = database.load_moneyForAccountInEvent(("ACC-004",))
    tipos = [fila[0] for fila in money]
    assert "MoneyDeposited" in tipos
    assert "AccountCreated" not in tipos
    assert database.load_moneyForAccountInEvent("ACC-004") == money


def test_store_money_for_account(isolated_db):
    database.crearCuenta("ACC-005", "Hugo")
    actualizadas = database.store_moneyForAccount(250.5, ("ACC-005",))
    assert actualizadas == 1
    info = database.load_accountInfo("ACC-005")
    assert info[2] == 250.5


def test_return_money_transfer_y_check_dup(isolated_db):
    database.save_event("ACC-006", "MoneyTransfer", {"amount": 10, "To": "ACC-007"})
    assert "ACC-006" in database.return_MoneyTransfer()
    dups = database.check_dup_accounts()
    assert dups == [1]


def test_ids_hipoteca_y_credito(isolated_db):
    assert database.generar_id_hypoteka() == "HYP-001"
    assert database.generar_id_credito() == "CRE-001"

    inicio = datetime(2026, 1, 1)
    fin = datetime(2036, 1, 1)
    database.cargar_nuevaHypoteka("ACC-001", "HYP-001", 100000, 3.5, inicio, fin, 500, 120)
    database.cargar_nuevaHypoteka("ACC-001", "CRE-001", 2000, 8, inicio, fin, 180, 12, credito=1)

    assert database.generar_id_hypoteka() == "HYP-002"
    assert database.generar_id_credito() == "CRE-002"


def test_buscar_listar_y_info_hipoteca(isolated_db):
    inicio = datetime(2026, 1, 1)
    fin = datetime(2031, 1, 1)
    database.crearCuenta("ACC-020", "Iris")
    database.cargar_nuevaHypoteka("ACC-020", "HYP-009", 50000, 2.9, inicio, fin, 400, 60)
    database.cargar_nuevaHypoteka("ACC-020", "CRE-009", 1000, 9, inicio, fin, 90, 12, credito=1)

    assert database.buscar_hypoteka_asociadaCuenta("ACC-020")[0] == "HYP-009"
    assert database.buscar_credito_asociadaCuenta("ACC-020")[0] == "CRE-009"

    hips = database.listar_hypotecasCreditos_asociados("ACC-020", 0)
    creds = database.listar_hypotecasCreditos_asociados("ACC-020", 1)
    assert hips[0][0] == "HYP-009"
    assert creds[0][0] == "CRE-009"

    assert database.listar_hypotecasCreditos_General(0)[0] == "HYP-009"
    assert database.listar_hypotecasCreditos_General(1)[0] == "CRE-009"

    info = database.obtenerInfoCreditoHypoteka("HYP-009")
    assert info[1] == "HYP-009"
    assert info[2] == 50000

    fila = database.buscar_hypoteka(1)
    assert fila is not None
    assert fila[0] == 50000


def test_guardar_y_actualizar_amortizacion(isolated_db):
    inicio = datetime(2026, 1, 1)
    fin = datetime(2031, 1, 1)
    database.cargar_nuevaHypoteka("ACC-030", "HYP-030", 20000, 3, inicio, fin, 200, 24)

    comision = database.guardar_amortizacion("HYP-030", "2026-06-01", 1000)
    assert comision == 5.0

    database.actualizar_hypotekaAmortizacion(
        {"nuevo_saldo": 19000, "meses_restantes": 22, "comision": 5.0},
        1,
        1000,
    )
    fila = database.buscar_hypoteka(1)
    assert fila[0] == 19000


def test_check_num_accounts_user(isolated_db):
    database.crearCuenta("ACC-041", "Ana")
    database.crearCuenta("ACC-042", "Ana")
    database.crearCuenta("ACC-043", "Luis")
    resultado = database.check_num_accounts_user()
    assert ("Ana", 2) in resultado
    assert ("Luis", 1) in resultado


def test_check_overdraft(isolated_db):
    database.crearCuenta("ACC-044", "Eva")
    database.store_moneyForAccount(-25, "ACC-044")
    cuentas = database.check_overdraft()
    assert cuentas[0][0] == "ACC-044"
    assert cuentas[0][1] == -25
