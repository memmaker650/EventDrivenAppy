from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import database
import gestionDatos
import hypotekas


@pytest.fixture
def gestor(fake_app, isolated_db):
    return gestionDatos.gestionDatos(fake_app)


def test_meses_entre_fechas(isolated_db):
    manager = hypotekas.HipotecaManager()
    meses = manager.meses_entre_fechas(datetime(2020, 1, 15), datetime(2022, 7, 15))
    assert meses == 30


def test_calcular_cuota_con_coma(isolated_db):
    manager = hypotekas.HipotecaManager()
    cuota = manager.calcular_cuota(120000, "3,5", 360)
    assert cuota == manager.calcular_cuota(120000, "3.5", 360)
    assert cuota > 0
    assert round(cuota * 360, 2) > 120000


def test_generar_cuadro_amortizacion(isolated_db):
    manager = hypotekas.HipotecaManager()
    cuota = manager.calcular_cuota(10000, "5", 12)
    cuadro = manager.generar_cuadro_amortizacion(10000, 5, cuota, 12)

    assert len(cuadro) == 12
    assert cuadro[0]["cuota"] == 1
    assert cuadro[-1]["pendiente"] < 1
    assert cuadro[0]["interes"] > 0


def test_amortizacion_anticipada(isolated_db):
    manager = hypotekas.HipotecaManager()
    resultado = manager.amortizacion_anticipada(10000, 2000)
    assert resultado["importe_amortizado"] == 2000
    assert resultado["comision"] == 10
    assert resultado["saldo_restante"] == 8000

    a_cero = manager.amortizacion_anticipada(500, 800)
    assert a_cero["saldo_restante"] == 0


def test_reducir_plazo_cancelacion_y_recalculo(isolated_db):
    manager = hypotekas.HipotecaManager()
    cancelada = manager.reducir_plazo_manteniendo_cuota(1000, 1000, 200, 3)
    assert cancelada["hipoteca_cancelada"] is True
    assert cancelada["meses_restantes"] == 0

    recorte = manager.reducir_plazo_manteniendo_cuota(10000, 2000, 300, 4)
    assert recorte["hipoteca_cancelada"] is False
    assert recorte["nuevo_saldo"] == 8000
    assert recorte["meses_restantes"] > 0
    assert recorte["comision"] == 10


def test_crear_hipoteca_y_credito(isolated_db):
    manager = hypotekas.HipotecaManager()
    inicio = datetime(2026, 1, 1)
    fin = datetime(2036, 1, 1)

    hyp_id, cuota_h = manager.crear_hipoteca("ACC-001", 80000, "3.0", inicio, fin)
    cre_id, cuota_c = manager.crear_hipoteca("ACC-001", 3000, "8.0", inicio, fin, credito=1)

    assert hyp_id.startswith("HYP-")
    assert cre_id.startswith("CRE-")
    assert cuota_h > 0
    assert cuota_c > 0
    assert database.obtenerInfoCreditoHypoteka(hyp_id) is not None
    assert database.obtenerInfoCreditoHypoteka(cre_id) is not None


def test_aplicar_amortizacion_reduciendo_plazo(isolated_db):
    manager = hypotekas.HipotecaManager()
    inicio = datetime(2026, 1, 1)
    fin = datetime(2031, 1, 1)
    manager.crear_hipoteca("ACC-040", 20000, "3.0", inicio, fin)

    resultado = manager.aplicar_amortizacion_reduciendo_plazo(1, 2000)
    assert resultado["nuevo_saldo"] == 18000
    assert resultado["hipoteca_cancelada"] is False

    with pytest.raises(ValueError, match="Hipoteca no encontrada"):
        manager.aplicar_amortizacion_reduciendo_plazo(999, 100)


def test_init_business_y_cargas(gestor, isolated_db):
    assert gestor.initBusiness() == "ACC-001"
    database.save_event("ACC-001", "AccountCreated", {"owner": "Ana"})
    database.crearCuenta("ACC-001", "Ana")

    assert gestor.load_accounts() == ["ACC-001"]
    assert gestor.load_accountInfo("ACC-001")[1] == "Ana"
    assert gestor.cargaEventosCompletos("ACC-001")[0][1] == "AccountCreated"
    assert gestor.domainAccount("ACC-001").owner == "Ana"


def test_create_account_ok(gestor, isolated_db):
    gestor.boton_execution = False
    gestor.create_account(None, "ACC-050", "Carla")
    assert gestor.app.estados[-1] == ("Cuenta creada", "OK")
    assert database.load_accountInfo("ACC-050")[1] == "Carla"


def test_create_account_con_comando(gestor, isolated_db):
    gestor.boton_execution = True
    gestor.create_account(None, "ACC-051", SimpleNamespace(value="Diego"))
    assert database.load_accountInfo("ACC-051")[1] == "Diego"
    eventos = database.load_events("ACC-051")
    assert eventos[0][0] == "AccountCreated"


def test_create_account_sin_owner(gestor):
    gestor.label_info = SimpleNamespace(text="")
    gestor.create_account(None, "ACC-052", "")
    assert gestor.label_info.text == "Debe indicar un nombre"


def test_create_account_owner_none(gestor, monkeypatch):
    avisos = []
    monkeypatch.setattr(gestionDatos, "mensajeUsuario", lambda msg, color: avisos.append(msg), raising=False)
    resultado = gestor.create_account(None, "ACC-053", None)
    assert resultado is False
    assert avisos


def test_create_account_block(gestor, isolated_db):
    gestor.create_account_block("ACC-060", "Elena")
    assert gestor.app.estados[-1] == ("Cuenta creada", "OK")

    gestor.label_info = SimpleNamespace(text="")
    gestor.create_account_block("ACC-061", "")
    assert gestor.label_info.text == "Debe indicar un nombre"


def test_ejecutar_accion_crear_y_movimientos(gestor, isolated_db):
    gestor.boton_execution = False
    gestor.ejecutarAccion(None, "crear", "ACC-070", 0, None, "Fran", None, None, None)
    assert database.load_accountInfo("ACC-070")[1] == "Fran"

    gestor.ejecutarAccion(None, "depositar", "ACC-070", 200, None, None, None, None, None)
    gestor.ejecutarAccion(None, "retirar", "ACC-070", 50, None, None, None, None, None)
    gestor.ejecutarAccion(None, "transferencia", "ACC-070", 20, "ACC-071", None, None, None, None)
    gestor.ejecutarAccion(None, "pago_tarjeta", "ACC-070", 15, None, None, "CorteIngles", None, None)

    tipos = [e[0] for e in database.load_events("ACC-070")]
    assert "MoneyDeposited" in tipos
    assert "Moneywithdraw" in tipos
    assert "MoneyTransfer" in tipos
    assert "CardPayment" in tipos


def test_ejecutar_accion_hipoteca_credito_y_pagos(gestor, isolated_db):
    gestor.ejecutarAccion(None, "pedir_hipoteca", "ACC-080", 50000, None, None, None, "3.0", 5)
    hyp = database.buscar_hypoteka_asociadaCuenta("ACC-080")
    assert hyp is not None

    gestor.ejecutarAccion(None, "pago_hipoteca", "ACC-080", 400, None, None, None, None, None)
    assert database.load_eventsOfType(hyp[0], "mortgagePayment")

    gestor.ejecutarAccion(None, "pedir_crédito", "ACC-081", 2000, None, None, None, "8.0", 2)
    cre = database.buscar_credito_asociadaCuenta("ACC-081")
    assert cre is not None

    gestor.ejecutarAccion(None, "pago_crédito", "ACC-081", 100, None, None, None, None, None)
    assert database.load_eventsOfType(cre[0], "CreditPayment")


def test_ejecutar_accion_sin_cuenta_hipoteca_credito(gestor):
    gestor.ejecutarAccion(None, "pedir_hipoteca", None, 1000, None, None, None, "3.0", 1)
    gestor.ejecutarAccion(None, "pedir_crédito", None, 1000, None, None, None, "8.0", 1)
    assert ("No hay cuenta asociada", "Error") in gestor.app.estados


def test_ejecutar_accion_cerrar(gestor, isolated_db):
    gestor.ejecutarAccion(None, "cerrar", "ACC-090", 0, None, None, None, None, None)
    tipos = [e[0] for e in database.load_events("ACC-090")]
    assert tipos == ["CloseAccount"]


def test_listar_y_traer_info_hyp_cred(gestor, isolated_db):
    manager = hypotekas.HipotecaManager()
    inicio = datetime(2026, 1, 1)
    fin = datetime(2031, 1, 1)
    hyp_id, _ = manager.crear_hipoteca("ACC-100", 15000, "2.5", inicio, fin)
    cre_id, _ = manager.crear_hipoteca("ACC-100", 800, "7", inicio, fin, credito=1)

    assert gestor.listar_hypotecasCreditos_asociados("ACC-100", "hip")[0][0] == hyp_id
    assert gestor.listar_hypotecasCreditos_asociados("ACC-100", "cre")[0][0] == cre_id
    assert gestor.traer_Info_CreditoHypoteka(hyp_id)[1] == hyp_id

    database.save_event(hyp_id, "mortgagePayment", {"amount": 200, "payment_date": "2026-02-01"})
    pagos = gestor.traer_EventosPago_CreditoHypoteka(hyp_id, "mortgagePayment")
    assert pagos == [(200.0, "2026-02-01")]


def test_calculo_eventos_a_cuenta_crea_y_actualiza(gestor, isolated_db):
    database.save_event("ACC-200", "AccountCreated", {"owner": "Gema"})
    database.save_event("ACC-200", "MoneyDeposited", {"amount": 100})
    database.save_event("ACC-200", "Moneywithdraw", {"amount": 30})

    gestor.calculoEventosACuenta(None)
    info = database.load_accountInfo("ACC-200")
    assert info[1] == "Gema"
    assert info[2] == 70.0
    assert "TERMINADO TRATAMIENTO EN BLOQUE" in gestor.label_info


def test_gestion_cuenta_al_dia_ramas(gestor):
    gestor.gestionCuentaAlDia(SimpleNamespace(value="depositar"), 10)
    gestor.gestionCuentaAlDia(SimpleNamespace(value="retirar"), 10)
    gestor.gestionCuentaAlDia(SimpleNamespace(value="transferencia"), 10)
    gestor.gestionCuentaAlDia(SimpleNamespace(value="cerrar"), 10)

    with patch.object(gestor, "create_account") as mock_create:
        gestor.gestionCuentaAlDia(SimpleNamespace(value="crear"), 0)
        mock_create.assert_called_once()
