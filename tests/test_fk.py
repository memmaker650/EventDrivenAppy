"""Claves foráneas activas en cada conexión (database.conectar)."""
import sqlite3
from datetime import datetime

import pytest

import commands
import database
import domain
import gestionDatos

INICIO = datetime(2026, 1, 1)
FIN = datetime(2031, 1, 1)


def test_cada_conexion_tiene_las_fk_activas(isolated_db):
    for _ in range(2):
        conn = database.get_connection()
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        conn.close()
    assert database.comprobar_FK_activas() is True


def test_account_id_es_unico(isolated_db):
    assert database.crearCuenta("ACC-001", "Ana") is True
    assert database.crearCuenta("ACC-001", "Otra") is False
    assert database.load_accounts() == ["ACC-001"]


def test_hipoteca_de_cuenta_inexistente_se_rechaza(isolated_db):
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        database.cargar_nuevaHypoteka("ACC-404", "HYP-001", 1000, 3, INICIO, FIN, 100, 12)

    database.crearCuenta("ACC-001", "Ana")
    database.cargar_nuevaHypoteka("ACC-001", "HYP-001", 1000, 3, INICIO, FIN, 100, 12)
    assert database.buscar_hypoteka_asociadaCuenta("ACC-001") == ("HYP-001",)


def test_no_se_borra_una_cuenta_con_hipotecas(isolated_db):
    database.crearCuenta("ACC-001", "Ana")
    database.cargar_nuevaHypoteka("ACC-001", "HYP-001", 1000, 3, INICIO, FIN, 100, 12)

    conn = database.get_connection()
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute("DELETE FROM accounts WHERE account_id = 'ACC-001'")
    conn.close()


def test_traspaso_a_historico_respeta_las_fk(isolated_db):
    database.crearCuenta("ACC-001", "Ana")
    database.cargar_nuevaHypoteka("ACC-001", "HYP-001", 1000, 3, INICIO, FIN, 100, 12)

    assert database.traspasoDatos_Accounts2Histo() is True
    assert database.load_accounts() == []


def test_comprobar_fk_detecta_filas_que_las_incumplen(isolated_db):
    # Fila huérfana metida sin FK (como podría haber en una BD antigua).
    conn = sqlite3.connect(isolated_db)
    conn.execute("""INSERT INTO hipotecas(cuenta_asociada, hipoteca_id, capital_inicial, tasa_anual, fecha_inicio,
                    fecha_fin, cuota_mensual, meses_totales, meses_restantes, saldo_actual)
                    VALUES ('ACC-404', 'HYP-001', 1, 1, 'x', 'x', 1, 1, 1, 1)""")
    conn.commit()
    conn.close()

    assert database.comprobar_FK_activas() is False


def test_bd_antigua_con_cuentas_duplicadas_no_rompe_el_arranque(tmp_path, monkeypatch):
    db_file = tmp_path / "antigua.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE accounts(id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT NOT NULL, "
                 "name TEXT NOT NULL, family_name TEXT NOT NULL, id_doc TEXT NOT NULL, email TEXT NOT NULL, "
                 "address TEXT, city TEXT, nationality TEXT, created_at DATE, state TEXT, money REAL)")
    for _ in range(2):
        conn.execute("INSERT INTO accounts(account_id, name, family_name, id_doc, email) "
                     "VALUES ('ACC-001', 'Ana', '', '', '')")
    conn.commit()
    conn.close()
    monkeypatch.setattr(database, "get_connection", lambda: database.conectar(str(db_file)))

    database.init_db()  # no lanza: registra el error del índice único

    # Sin índice único la FK de hipotecas no es utilizable y se informa.
    assert database.comprobar_FK_activas() is False


def test_pedir_prestamo_para_cuenta_inexistente_avisa_sin_grabar(fake_app, isolated_db):
    gestor = gestionDatos.gestionDatos(fake_app)

    assert gestor.ejecutarAccion(None, accion="pedir_hipoteca", origen="ACC-404", cantidad=1000,
                                 rate="3", return_period=5) is False

    assert fake_app.estados == [("La cuenta ACC-404 no existe", "Error")]
    assert database.load_all_events() == []


def test_batch_omite_prestamos_sin_cuenta_y_guarda_el_resto(fake_app, isolated_db):
    domain.handle_create_account(commands.CreateAccount("ACC-001", "Ana"))
    domain.handle_deposit(commands.DepositMoney("ACC-001", 100))
    domain.handle_demandMortgage(commands.DemandMortgage(
        "ACC-001", "HYP-001", 3, 1000, 5, "2026-01-01T00:00:00"))
    # Préstamo de una cuenta que no existe ni en eventos ni en accounts.
    domain.handle_demandCredit(commands.DemandCredit(
        "ACC-404", "CRE-001", 7, 500, 1, "2026-01-01T00:00:00"))
    # Cuenta creada sin evento AccountCreated pero existente en accounts: su préstamo sí entra.
    database.crearCuenta("ACC-002", "Luis")
    domain.handle_demandMortgage(commands.DemandMortgage(
        "ACC-002", "HYP-002", 3, 2000, 5, "2026-01-01T00:00:00"))

    gestor = gestionDatos.gestionDatos(fake_app)
    proyeccion = gestor.calculoEventosACuenta(None)

    assert proyeccion.loans_without_account == ["CRE-001"]
    assert fake_app.estados[-1] == (
        "TERMINADO TRATAMIENTO EN BLOQUE !! 5 eventos, 0 ignorados, 1 préstamos sin cuenta", "warning")
    assert database.load_accountInfo("ACC-001")[2] == 100.0
    assert database.buscar_hypoteka_asociadaCuenta("ACC-001") == ("HYP-001",)
    assert database.buscar_hypoteka_asociadaCuenta("ACC-002") == ("HYP-002",)
    assert database.obtenerInfoCreditoHypoteka("CRE-001") is None
