"""Batch de ficheros de entrada: operaciones, resumen global, log y validaciones."""
import json
import logging
import shutil
from pathlib import Path

import daemonInput
import database
import gestionDatos

FICHERO_EJEMPLO = Path(__file__).parent / "datos" / "entrada_batch.json"

ERRORES_EJEMPLO = [
    (5, "AccountCreated", "ACC-010", "Error!!! Cuenta NO creada, EMAIL NO rellenado."),
    (6, "AccountCreated", "ACC-011", "Error!!! Cuenta NO creada, CIUDAD NO rellenado."),
    (20, "MoneyDeposited", "ACC-010", "La cuenta ACC-010 no existe"),
    (21, "MoneyDeposited", "ACC-011", "La cuenta ACC-011 no existe"),
    (42, "MoneyTransfer", "ACC-009", "La cuenta ACC-099 no existe"),
    (43, "Moneywithdraw", "ACC-009", "Cantidad no válida: '-50' (debe ser un número mayor que 0)"),
    (44, "mortgagePayment", "ACC-007", "No hay hipoteca asociada"),
    (51, "MoneyDeposited", "ACC-008", "La cuenta ACC-008 está cerrada"),
]


def _escribir(carpeta, nombre, operaciones):
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    ruta.write_text(json.dumps(operaciones), encoding="utf-8")
    return ruta


def _alta(cuenta, owner="Ana", **extra):
    datos = dict(account_id=cuenta, owner=owner, family_name="Ruiz", doc_id="1", email="a@b.es",
                 address="C/ A", city="Lugo", nationality="ES - España")
    datos.update(extra)
    return {"aggregate_id": cuenta, "event_type": "AccountCreated", "event_data": datos}


def _op(cuenta, tipo, **datos):
    return {"aggregate_id": cuenta, "event_type": tipo, "event_data": {"account_id": cuenta, **datos}}


def test_fichero_de_ejemplo_completo(isolated_db, carpetas_batch):
    carpetas_batch["input"].mkdir(parents=True)
    shutil.copy(FICHERO_EJEMPLO, carpetas_batch["input"] / "entrada1.json")

    resumen = daemonInput.ejecutar_batch()

    assert (resumen.tratadas, resumen.correctas, resumen.errores) == (51, 43, 8)
    errores = [(o.numero, o.tipo, o.cuenta, o.mensaje) for o in resumen.operaciones if not o.ok]
    assert errores == ERRORES_EJEMPLO

    saldos = {c: database.load_accountInfo(c)[2] for c in ("ACC-006", "ACC-007", "ACC-008", "ACC-009")}
    assert saldos == {"ACC-006": 5094.53, "ACC-007": 6824.0, "ACC-008": 1753.28, "ACC-009": 4449.27}
    assert database.load_accountInfo("ACC-008")[3] == "closed"
    assert database.load_accountInfo("ACC-010") is None
    assert database.buscar_hypoteka_asociadaCuenta("ACC-006") == ("HYP-001",)
    assert database.buscar_credito_asociadaCuenta("ACC-007") == ("CRE-001",)

    # El fichero sale de input y queda en tratados.
    assert list(carpetas_batch["input"].iterdir()) == []
    assert [p.name for p in carpetas_batch["tratados"].iterdir()] == ["entrada1.json"]


def test_resumen_global_en_texto_y_linea(isolated_db, carpetas_batch):
    _escribir(carpetas_batch["input"], "e.json", [
        _alta("ACC-001"),
        _op("ACC-001", "MoneyDeposited", amount=100),
        _op("ACC-001", "MoneyDeposited", amount="abc"),
    ])

    resumen = daemonInput.ejecutar_batch()
    texto = resumen.texto()

    assert resumen.linea() == ("Batch: 3 operaciones tratadas, 2 correctas, 1 en error · "
                               "movimientos (2 eventos, 0 ignorados)")
    assert "Operaciones tratadas: 3" in texto
    assert "  Correctas: 2" in texto
    assert "  En error:  1" in texto
    assert "  MoneyDeposited     2  (ok 1, error 1)" in texto
    assert "[e.json #3] ERROR MoneyDeposited ACC-001: Cantidad no válida: 'abc'" in texto


def test_resumen_y_operaciones_quedan_en_el_log(isolated_db, carpetas_batch, caplog):
    _escribir(carpetas_batch["input"], "e.json", [_alta("ACC-001"), _op("ACC-404", "MoneyDeposited", amount=5)])

    with caplog.at_level(logging.INFO, logger="daemonInput"):
        daemonInput.ejecutar_batch()

    mensajes = [(r.levelname, r.getMessage()) for r in caplog.records if r.name == "daemonInput"]
    assert ("INFO", "[e.json #1] OK    AccountCreated ACC-001: Cuenta creada") in mensajes
    assert ("WARNING", "[e.json #2] ERROR MoneyDeposited ACC-404: La cuenta ACC-404 no existe") in mensajes
    assert ("INFO", "Operaciones tratadas: 2") in mensajes
    assert ("INFO", "  En error:  1") in mensajes


def test_operacion_desconocida_o_rota_no_para_el_fichero(isolated_db, carpetas_batch):
    _escribir(carpetas_batch["input"], "e.json", [
        _op("ACC-001", "BlanqueoCapitales", amount=1),
        "esto no es una operación",
        _alta("ACC-001"),
    ])

    resumen = daemonInput.procesar_carpeta_entrada()

    assert [(o.ok, o.mensaje) for o in resumen.operaciones] == [
        (False, "Tipo de operación desconocido: BlanqueoCapitales"),
        (False, "Excepción: la operación no es un objeto JSON"),
        (True, "Cuenta creada"),
    ]


def test_fichero_ilegible_va_a_error(isolated_db, carpetas_batch):
    carpetas_batch["input"].mkdir(parents=True)
    (carpetas_batch["input"] / "roto.json").write_text("{no-es-json", encoding="utf-8")
    _escribir(carpetas_batch["input"], "objeto.json", {"no": "es una lista"})

    resumen = daemonInput.procesar_carpeta_entrada()

    assert [n for n, _ in resumen.ficheros_error] == ["objeto.json", "roto.json"]
    assert sorted(p.name for p in carpetas_batch["error"].iterdir()) == ["objeto.json", "roto.json"]
    assert resumen.linea().startswith("Batch: 0 operaciones tratadas, 0 correctas, 0 en error, 2 ficheros ilegibles")


def test_no_pisa_un_fichero_ya_tratado(isolated_db, carpetas_batch):
    _escribir(carpetas_batch["tratados"], "e.json", [])
    _escribir(carpetas_batch["input"], "e.json", [_alta("ACC-001")])

    resumen = daemonInput.procesar_carpeta_entrada()

    nombres = sorted(p.name for p in carpetas_batch["tratados"].iterdir())
    assert len(nombres) == 2 and nombres[0] == "e.json" and nombres[1].startswith("e_")
    assert resumen.ficheros[0][1].name == nombres[1]


def test_sin_ficheros_pendientes(isolated_db, carpetas_batch):
    resumen = daemonInput.ejecutar_batch()
    assert resumen.tratadas == 0
    assert resumen.linea() == "Batch: sin ficheros pendientes · movimientos (0 eventos, 0 ignorados)"


class AppConResumen:
    def __init__(self):
        self.estados = []
        self.resumenes = []

    def actualizar_estado(self, mensaje, tipo):
        self.estados.append((mensaje, tipo))

    def mostrar_resumen(self, texto):
        self.resumenes.append(texto)


def test_boton_batch_procesa_ficheros_y_muestra_resumen(isolated_db, carpetas_batch):
    _escribir(carpetas_batch["input"], "e.json", [
        _alta("ACC-001"),
        _op("ACC-001", "MoneyDeposited", amount=100),
        _op("ACC-002", "MoneyDeposited", amount=100),
    ])
    app = AppConResumen()

    assert gestionDatos.gestionDatos(app).lanzar_BatchTratarEventos(None) is True

    assert app.estados[-1] == (
        "Batch: 3 operaciones tratadas, 2 correctas, 1 en error · movimientos (2 eventos, 0 ignorados)",
        "warning",
    )
    assert len(app.resumenes) == 1 and "Operaciones tratadas: 3" in app.resumenes[0]
    assert database.load_accountInfo("ACC-001")[2] == 100.0


def test_boton_batch_todo_correcto_en_verde(isolated_db, carpetas_batch):
    _escribir(carpetas_batch["input"], "e.json", [_alta("ACC-001"), _op("ACC-001", "MoneyDeposited", amount=1)])
    app = AppConResumen()

    gestionDatos.gestionDatos(app).lanzar_BatchTratarEventos(None)

    assert app.estados[-1][1] == "OK"


def test_validaciones_de_operacion(fake_app, isolated_db):
    g = gestionDatos.gestionDatos(fake_app)
    database.crearCuenta("ACC-001", "Ana")
    database.crearCuenta("ACC-002", "Luis")
    database.actualizar_estado_cuenta("ACC-002", "closed")

    casos = [
        (dict(accion="depositar", origen="ACC-001", cantidad="abc"),
         "Cantidad no válida: 'abc' (debe ser un número mayor que 0)"),
        (dict(accion="retirar", origen="ACC-001", cantidad=0),
         "Cantidad no válida: '0' (debe ser un número mayor que 0)"),
        (dict(accion="pago_tarjeta", origen="ACC-001", cantidad=5), "Falta la tienda del pago con tarjeta"),
        (dict(accion="transferencia", origen="ACC-001", cantidad=5), "Falta la cuenta destino"),
        (dict(accion="transferencia", origen="ACC-001", cantidad=5, destino="ACC-001"),
         "La cuenta destino no puede ser la de origen"),
        (dict(accion="transferencia", origen="ACC-001", cantidad=5, destino="ACC-002"), "La cuenta ACC-002 está cerrada"),
        (dict(accion="cerrar", origen="ACC-002", cantidad=0), "La cuenta ACC-002 está cerrada"),
        (dict(accion="volar", origen="ACC-001", cantidad=5), "Acción desconocida: volar"),
    ]
    for kwargs, esperado in casos:
        assert g.ejecutarAccion(None, **kwargs) is False, kwargs
        assert fake_app.estados[-1] == (esperado, "Error"), kwargs

    assert database.load_all_events() == []
