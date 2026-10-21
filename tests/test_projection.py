"""Batch de reprocesado: proyección de solo lectura sobre event_store."""
from decimal import Decimal

import commands
import daemonInput
import database
import domain
import gestionDatos


def _num_eventos():
    return len(database.load_all_events())


def _cuenta(account_id):
    conn = database.get_connection()
    fila = conn.execute(
        "SELECT name, email, state, money FROM accounts WHERE account_id = ?",
        (account_id,),
    ).fetchall()
    conn.close()
    assert len(fila) <= 1, f"{account_id} duplicada en accounts"
    return fila[0] if fila else None


def _hipotecas():
    conn = database.get_connection()
    filas = conn.execute(
        "SELECT cuenta_asociada, hipoteca_id, capital_inicial, fecha_inicio, "
        "fecha_fin, meses_totales, es_Credito FROM hipotecas ORDER BY hipoteca_id"
    ).fetchall()
    conn.close()
    return filas


def _alta(account_id, owner):
    domain.handle_create_account(commands.CreateAccount(account_id, owner))


def test_batch_no_graba_eventos_y_es_idempotente(isolated_db):
    _alta("ACC-001", "Ana")
    domain.handle_deposit(commands.DepositMoney("ACC-001", "100"))
    domain.handle_withdraw(commands.MoneyWithDraw("ACC-001", "30"))

    for _ in range(3):
        domain.rebuild_read_model()
        assert _num_eventos() == 3
        assert _cuenta("ACC-001")[3] == 70.0


def test_transferencia_resta_al_origen_y_suma_al_destino(isolated_db):
    _alta("ACC-001", "Ana")
    _alta("ACC-002", "Luis")
    domain.handle_deposit(commands.DepositMoney("ACC-001", 100))
    domain.handle_moneyTransfer(commands.TransferMoney("ACC-001", 40, "ACC-002"))

    domain.rebuild_read_model()

    assert _cuenta("ACC-001")[3] == 60.0
    assert _cuenta("ACC-002")[3] == 40.0


def test_importes_en_texto_con_coma_sin_perder_decimales(isolated_db):
    _alta("ACC-001", "Ana")
    domain.handle_deposit(commands.DepositMoney("ACC-001", "10,50"))
    domain.handle_withdraw(commands.MoneyWithDraw("ACC-001", "0.25"))
    domain.handle_CardPayment(commands.CardPayment("ACC-001", 0.1, "Bar"))

    domain.rebuild_read_model()

    assert domain.load_account("ACC-001").balance == Decimal("10.15")
    assert _cuenta("ACC-001")[3] == 10.15


def test_overdraft_resta_y_cierre_cambia_estado(isolated_db):
    _alta("ACC-001", "Ana")
    domain.handle_deposit(commands.DepositMoney("ACC-001", 50))
    domain.handle_Overdraft(commands.Overdraft("ACC-001", 5))
    domain.handle_close_account(commands.CloseAccount("ACC-001"))

    domain.rebuild_read_model()

    assert _cuenta("ACC-001")[2:] == ("closed", 45.0)


def test_prestamos_mueven_saldo_de_la_cuenta_asociada(isolated_db):
    _alta("ACC-001", "Ana")
    domain.handle_deposit(commands.DepositMoney("ACC-001", 1000))
    domain.handle_demandMortgage(commands.DemandMortgage(
        "ACC-001", "HYP-007", "3,5", 100000, 20, "2026-01-15T10:00:00"))
    domain.handle_mortgagePayment(commands.MortgagePayment("HYP-007", 500, "2026-02-15"))
    domain.handle_mortgageAmortisation(
        commands.MortgageAmortisation("HYP-007", 100, "2026-03-15"))
    domain.handle_demandCredit(commands.DemandCredit(
        "ACC-001", "CRE-003", 8, 2000, 2, "2026-01-01T00:00:00"))
    domain.handle_CreditPayment(commands.CreditPayment("CRE-003", 90, "2026-02-01"))

    domain.rebuild_read_model()

    # 1000 + 2000 (crédito ingresado) - 500 - 100 - 90; la hipoteca no ingresa.
    assert _cuenta("ACC-001")[3] == 2310.0
    # No hay cuentas falsas creadas a partir de los streams HYP-/CRE-.
    assert database.load_accounts() == ["ACC-001"]


def test_prestamos_se_reconstruyen_con_su_id_y_fecha_originales(isolated_db):
    _alta("ACC-001", "Ana")
    domain.handle_demandMortgage(commands.DemandMortgage(
        "ACC-001", "HYP-007", "3.5", 100000, 20, "2026-01-15T10:00:00"))
    domain.handle_demandCredit(commands.DemandCredit(
        "ACC-001", "CRE-003", "0", 1200, 1, "2026-01-01T00:00:00"))

    domain.rebuild_read_model()
    domain.rebuild_read_model()

    assert _hipotecas() == [
        ("ACC-001", "CRE-003", 1200.0, "2026-01-01", "2027-01-01", 12, 1),
        ("ACC-001", "HYP-007", 100000.0, "2026-01-15", "2046-01-15", 240, 0),
    ]
    assert database.obtenerInfoCreditoHypoteka("CRE-003")[5] == 100.0  # tasa 0
    assert _num_eventos() == 3


def test_pagos_sin_fecha_se_aplican(isolated_db):
    _alta("ACC-001", "Ana")
    domain.handle_demandCredit(commands.DemandCredit(
        "ACC-001", "CRE-003", 8, 2000, 2, "2026-01-01T00:00:00"))
    domain.handle_CreditPayment(commands.CreditPayment("CRE-003", 90, None))
    # Registro antiguo sin la clave payment_date.
    database.save_event("CRE-003", "CreditPayment", {"credit_id": "CRE-003", "amount": 10})

    proyeccion = domain.rebuild_read_model()

    assert proyeccion.skipped == []
    assert _cuenta("ACC-001")[3] == 1900.0


def test_eventos_invalidos_se_ignoran_sin_parar_el_batch(isolated_db):
    _alta("ACC-001", "Ana")
    database.save_event("ACC-001", "NoExiste", {"amount": 1})
    database.save_event("ACC-001", "MoneyDeposited", {"amount": "abc"})
    database.save_event("HYP-999", "mortgagePayment",
                        {"mortgage_id": "HYP-999", "amount": 5, "payment_date": "x"})
    domain.handle_deposit(commands.DepositMoney("ACC-001", 20))

    proyeccion = domain.rebuild_read_model()

    assert proyeccion.processed == 2
    assert len(proyeccion.skipped) == 3
    assert _cuenta("ACC-001")[3] == 20.0


def test_conserva_datos_que_no_viajan_en_eventos(isolated_db):
    database.crearCuenta("ACC-001", "Ana", "Ruiz", "123", "ana@x.es", "C/ Sol", "Madrid", "ES")
    _alta("ACC-001", "Ana")
    domain.handle_deposit(commands.DepositMoney("ACC-001", 15))

    domain.rebuild_read_model()

    assert _cuenta("ACC-001") == ("Ana", "ana@x.es", "open", 15.0)


def test_historiza_antes_de_actualizar(isolated_db):
    database.crearCuenta("ACC-001", "Ana")
    _alta("ACC-001", "Ana")
    domain.handle_deposit(commands.DepositMoney("ACC-001", 15))

    domain.rebuild_read_model()

    conn = database.get_connection()
    histo = conn.execute("SELECT account_id, money FROM accounts_histo").fetchall()
    conn.close()
    assert histo == [("ACC-001", 0.0)]


def test_movimientos_sin_alta_no_crean_cuenta(isolated_db):
    domain.handle_deposit(commands.DepositMoney("ACC-005", 10))

    proyeccion = domain.rebuild_read_model()

    assert "ACC-005" in proyeccion.accounts
    assert _cuenta("ACC-005") is None


def test_load_account_y_tabla_usan_el_mismo_calculo(isolated_db):
    _alta("ACC-001", "Ana")
    _alta("ACC-002", "Luis")
    domain.handle_deposit(commands.DepositMoney("ACC-002", 80))
    domain.handle_moneyTransfer(commands.TransferMoney("ACC-002", 30, "ACC-001"))

    domain.rebuild_read_model()

    for account_id in ("ACC-001", "ACC-002"):
        assert float(domain.load_account(account_id).balance) == _cuenta(account_id)[3]


def test_entradas_ui_y_demonio_usan_la_proyeccion(isolated_db, fake_app):
    _alta("ACC-001", "Ana")
    domain.handle_deposit(commands.DepositMoney("ACC-001", 10))

    assert gestionDatos.gestionDatos(fake_app).lanzar_BatchTratarEventos(None) is True
    assert daemonInput.ProcesadoDatosDemonio().procesar_EventosDB() is True

    assert fake_app.estados[-1][1] == "OK"
    assert _num_eventos() == 2
    assert _cuenta("ACC-001")[3] == 10.0
