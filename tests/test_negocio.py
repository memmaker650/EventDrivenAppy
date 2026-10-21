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
    database.crearCuenta("ACC-001", "Titular")  # la FK exige que la cuenta exista
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
    database.crearCuenta("ACC-040", "Titular")  # la FK exige que la cuenta exista
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


# Datos del formulario de alta: todos obligatorios desde la UI.
FORMULARIO = dict(
    family="Soler",
    idcardnumber="12345678Z",
    email="cliente@correo.es",
    address="C/ Mayor 1",
    city="Madrid",
    nationality="ES - España",
)


def test_create_account_ok(gestor, isolated_db):
    assert gestor.create_account(None, "ACC-050", "Carla", **FORMULARIO) is True
    assert gestor.app.estados[-1] == ("Cuenta creada", "OK")
    assert database.load_accountInfo("ACC-050")[1] == "Carla"


def test_create_account_desde_ui_graba_evento(gestor, isolated_db):
    gestor.create_account(None, "ACC-051", "Diego", **FORMULARIO)
    assert database.load_accountInfo("ACC-051")[1] == "Diego"
    eventos = database.load_events("ACC-051")
    assert [e[0] for e in eventos] == ["AccountCreated"]


def test_create_account_desde_eventos_no_regraba_evento(gestor, isolated_db):
    assert gestor.create_account(None, "ACC-054", "Lola", desde_eventos=True) is True
    assert database.load_accountInfo("ACC-054")[1] == "Lola"
    assert database.load_events("ACC-054") == []


def test_create_account_sin_owner(gestor, isolated_db):
    assert gestor.create_account(None, "ACC-052", "", **FORMULARIO) is False
    assert gestor.app.estados[-1] == ("Error!!! Cuenta NO creada, NOMBRE NO rellenado.", "Error")
    assert database.load_accountInfo("ACC-052") is None


def test_create_account_campo_obligatorio_vacio(gestor, isolated_db):
    incompleto = dict(FORMULARIO, email="")
    assert gestor.create_account(None, "ACC-055", "Luz", **incompleto) is False
    assert gestor.app.estados[-1] == ("Error!!! Cuenta NO creada, EMAIL NO rellenado.", "Error")


def test_create_account_owner_none(gestor, isolated_db):
    assert gestor.create_account(None, "ACC-053", None, desde_eventos=True) is False
    assert gestor.app.estados[-1] == ("Error!!! Cuenta NO creada, NOMBRE NO rellenado.", "Error")
    assert database.load_events("ACC-053") == []


def test_create_account_block(gestor, isolated_db):
    gestor.create_account_block("ACC-060", "Elena")
    assert gestor.app.estados[-1] == ("Cuenta creada", "OK")

    gestor.label_info = SimpleNamespace(text="")
    gestor.create_account_block("ACC-061", "")
    assert gestor.label_info.text == "Debe indicar un nombre"


def test_ejecutar_accion_crear_y_movimientos(gestor, isolated_db):
    gestor.ejecutarAccion(
        None, accion="crear", origen="ACC-070", cantidad=0, propietario="Fran",
        apellidos="Gil", doc_id="1", email="f@g.es", address="C/ A", city="Lugo",
        nationality="ES - España",
    )
    assert database.load_accountInfo("ACC-070")[1] == "Fran"

    gestor.ejecutarAccion(None, accion="depositar", origen="ACC-070", cantidad=200)
    gestor.ejecutarAccion(None, accion="retirar", origen="ACC-070", cantidad=50)
    gestor.ejecutarAccion(None, accion="transferencia", origen="ACC-070", cantidad=20, destino="ACC-071")
    gestor.ejecutarAccion(None, accion="pago_tarjeta", origen="ACC-070", cantidad=15, tienda="CorteIngles")

    eventos = database.load_events("ACC-070")
    tipos = [e[0] for e in eventos]
    assert tipos == ["AccountCreated", "MoneyDeposited", "Moneywithdraw", "MoneyTransfer", "CardPayment"]
    assert '"shop": "CorteIngles"' in eventos[-1][1]


def test_ejecutar_accion_hipoteca_credito_y_pagos(gestor, isolated_db):
    database.crearCuenta("ACC-080", "Titular")  # la FK exige que la cuenta exista
    gestor.ejecutarAccion(None, accion="pedir_hipoteca", origen="ACC-080", cantidad=50000,
                          rate="3,0", return_period="5", dateInicio="2026-01-15T00:00:00")
    hyp = database.buscar_hypoteka_asociadaCuenta("ACC-080")
    assert hyp is not None

    # El evento y la fila de hipotecas comparten id y fecha de inicio.
    demanda = database.load_eventsOfType("ACC-080", "demandMortgage")
    assert len(demanda) == 1
    assert f'"mortgage_id": "{hyp[0]}"' in demanda[0][2]
    assert database.obtenerInfoCreditoHypoteka(hyp[0])[4] == "2026-01-15"

    gestor.ejecutarAccion(None, accion="pago_hipoteca", origen="ACC-080", cantidad=400)
    assert database.load_eventsOfType(hyp[0], "mortgagePayment")

    gestor.ejecutarAccion(None, accion="pedir_crédito", origen="ACC-080", cantidad=2000,
                          rate="8.0", return_period=2)
    cre = database.buscar_credito_asociadaCuenta("ACC-080")
    assert cre is not None
    assert cre[0].startswith("CRE-")
    # Con un crédito ya creado, la hipoteca sigue siendo la misma.
    assert database.buscar_hypoteka_asociadaCuenta("ACC-080") == hyp

    gestor.ejecutarAccion(None, accion="pago_crédito", origen="ACC-080", cantidad=100)
    assert database.load_eventsOfType(cre[0], "CreditPayment")


def test_ejecutar_accion_ids_de_hipoteca_no_se_mezclan_con_creditos(gestor, isolated_db):
    database.crearCuenta("ACC-082", "Titular")  # la FK exige que la cuenta exista
    gestor.ejecutarAccion(None, accion="pedir_crédito", origen="ACC-082", cantidad=900,
                          rate="5", return_period=1)
    gestor.ejecutarAccion(None, accion="pedir_hipoteca", origen="ACC-082", cantidad=9000,
                          rate="2", return_period=10)
    assert database.buscar_hypoteka_asociadaCuenta("ACC-082") == ("HYP-001",)


def test_ejecutar_accion_sin_cuenta_hipoteca_credito(gestor, isolated_db):
    gestor.ejecutarAccion(None, accion="pedir_hipoteca", origen=None, cantidad=1000, rate="3.0", return_period=1)
    gestor.ejecutarAccion(None, accion="pedir_crédito", origen=None, cantidad=1000, rate="8.0", return_period=1)
    assert gestor.app.estados == [("No hay cuenta asociada", "Error")] * 2
    assert database.load_all_events() == []


def test_ejecutar_accion_prestamo_datos_invalidos_no_graba_evento(gestor, isolated_db):
    database.crearCuenta("ACC-083", "Titular")  # la FK exige que la cuenta exista
    gestor.ejecutarAccion(None, accion="pedir_hipoteca", origen="ACC-083", cantidad=1000, rate="3", return_period="")
    gestor.ejecutarAccion(None, accion="pedir_crédito", origen="ACC-083", cantidad=1000, rate="", return_period=2)
    assert gestor.app.estados == [
        ("Periodo de retorno (AÑOS) no válido", "Error"),
        ("Tasa de interés o cantidad no válida", "Error"),
    ]
    assert database.load_all_events() == []


def test_operaciones_confirman_en_verde(gestor, isolated_db):
    database.crearCuenta("ACC-087", "Titular")  # la FK exige que la cuenta exista
    assert gestor.ejecutarAccion(None, accion="depositar", origen="ACC-087", cantidad="100,5") is True
    assert gestor.ejecutarAccion(None, accion="retirar", origen="ACC-087", cantidad=20) is True
    assert gestor.ejecutarAccion(None, accion="pago_tarjeta", origen="ACC-087", cantidad=5, tienda="Bar") is True
    assert gestor.ejecutarAccion(None, accion="transferencia", origen="ACC-087", cantidad=10, destino="ACC-088") is True
    assert gestor.ejecutarAccion(None, accion="pedir_crédito", origen="ACC-087", cantidad=900, rate="5", return_period=1) is True

    assert gestor.app.estados == [
        ("Depósito de 100,5 € registrado en ACC-087", "OK"),
        ("Retirada de 20 € registrada en ACC-087", "OK"),
        ("Pago con tarjeta de 5 € en Bar registrado en ACC-087", "OK"),
        ("Transferencia de 10 € de ACC-087 a ACC-088 registrada", "OK"),
        ("Crédito CRE-001 de 900 € registrado en ACC-087", "OK"),
    ]


def test_operacion_no_guardada_avisa_en_rojo(gestor, isolated_db, monkeypatch):
    database.crearCuenta("ACC-089", "Titular")  # la FK exige que la cuenta exista
    import domain
    monkeypatch.setattr(domain, "save_event",
                        lambda *a: {"ok": False, "id": None, "mensaje": "database is locked"})

    assert gestor.ejecutarAccion(None, accion="depositar", origen="ACC-089", cantidad=10) is False
    assert gestor.ejecutarAccion(None, accion="pedir_hipoteca", origen="ACC-089", cantidad=900,
                                 rate="2", return_period=5) is False

    assert gestor.app.estados == [("ERROR al guardar en BD: database is locked", "Error")] * 2
    # Si el evento no se guardó, tampoco se crea la fila de la hipoteca.
    assert database.buscar_hypoteka_asociadaCuenta("ACC-089") is None


def test_pagos_sin_fecha_quedan_sin_fecha(gestor, isolated_db):
    database.crearCuenta("ACC-085", "Titular")  # la FK exige que la cuenta exista
    gestor.ejecutarAccion(None, accion="pedir_hipoteca", origen="ACC-085", cantidad=9000, rate="2", return_period=10)
    gestor.ejecutarAccion(None, accion="pedir_crédito", origen="ACC-085", cantidad=900, rate="5", return_period=1)
    hyp = database.buscar_hypoteka_asociadaCuenta("ACC-085")[0]
    cre = database.buscar_credito_asociadaCuenta("ACC-085")[0]

    gestor.ejecutarAccion(None, accion="pago_hipoteca", origen="ACC-085", cantidad=100)
    gestor.ejecutarAccion(None, accion="pago_hipoteca", origen="ACC-085", cantidad=100, dateInicio="")
    gestor.ejecutarAccion(None, accion="pago_hipoteca", origen="ACC-085", cantidad=100, dateInicio="2026-05-01")
    gestor.ejecutarAccion(None, accion="pago_crédito", origen="ACC-085", cantidad=50)

    assert gestor.traer_EventosPago_CreditoHypoteka(hyp, "mortgagePayment") == [
        (100.0, None), (100.0, None), (100.0, "2026-05-01"),
    ]
    assert gestor.traer_EventosPago_CreditoHypoteka(cre, "CreditPayment") == [(50.0, None)]


def test_cuenta_muestra_eventos_de_sus_prestamos(gestor, isolated_db):
    database.crearCuenta("ACC-086", "Titular")  # la FK exige que la cuenta exista
    gestor.ejecutarAccion(None, accion="pedir_crédito", origen="ACC-086", cantidad=900, rate="5", return_period=1)
    gestor.ejecutarAccion(None, accion="pago_crédito", origen="ACC-086", cantidad=50)

    tipos = [e[1] for e in gestor.cargaEventosCompletos("ACC-086")]
    assert tipos == ["demandCredit", "CreditPayment"]


def test_ejecutar_accion_pago_hipoteca_sin_hipoteca(gestor, isolated_db):
    gestor.ejecutarAccion(None, accion="pago_hipoteca", origen="ACC-084", cantidad=100)
    assert gestor.app.estados[-1] == ("No hay hipoteca asociada", "Error")
    assert database.load_all_events() == []


def test_ejecutar_accion_cerrar(gestor, isolated_db):
    gestor.ejecutarAccion(None, "cerrar", "ACC-090", 0, None, None, None, None, None)
    tipos = [e[0] for e in database.load_events("ACC-090")]
    assert tipos == ["CloseAccount"]


def test_listar_y_traer_info_hyp_cred(gestor, isolated_db):
    database.crearCuenta("ACC-100", "Titular")  # la FK exige que la cuenta exista
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
