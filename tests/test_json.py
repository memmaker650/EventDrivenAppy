import json
from pathlib import Path
from unittest.mock import MagicMock

import daemonInput


def test_procesar_json_extrae_campos():
    procesador = daemonInput.ProcesadoDatosDemonio()
    procesador.procesar_json(
        {
            "aggregate_id": "ACC-001",
            "event_type": "depositar",
            "event_data": {
                "account": "ACC-001",
                "amount": "150.5",
                "owner": "Ana",
                "destiny": "ACC-002",
            },
        }
    )

    assert procesador.aggregate_id == "ACC-001"
    assert procesador.event_type == "depositar"
    assert procesador.account == "ACC-001"
    assert procesador.amount == 150.5
    assert procesador.owner == "Ana"
    assert procesador.destiny == "ACC-002"


def test_procesar_json_valores_por_defecto():
    procesador = daemonInput.ProcesadoDatosDemonio()
    procesador.procesar_json({"aggregate_id": "ACC-002", "event_type": "crear"})

    assert procesador.amount == 0.0
    assert procesador.account is None
    assert procesador.owner is None
    assert procesador.destiny is None


def test_leer_datos_json():
    procesador = daemonInput.ProcesadoDatosDemonio()
    datos = procesador.leerDatosJSON('{"amount": "20", "payment_date": "2026-01-10"}')
    assert datos["amount"] == "20"
    assert datos["payment_date"] == "2026-01-10"


def test_procesar_json_hyp_cred():
    procesador = daemonInput.ProcesadoDatosDemonio()
    amount, fecha = procesador.procesar_json_hypCred(
        {"account": "HYP-001", "amount": "430.10", "payment_date": "2026-03-01"}
    )

    assert procesador.mortgage_id == "HYP-001"
    assert amount == 430.10
    assert fecha == "2026-03-01"


def test_procesar_fichero_ok_mueve_a_tratados(tmp_path, monkeypatch):
    entrada = tmp_path / "entrada"
    tratados = tmp_path / "tratados"
    error = tmp_path / "error"
    entrada.mkdir()
    tratados.mkdir()
    error.mkdir()

    payload = [
        {
            "aggregate_id": "ACC-020",
            "event_type": "depositar",
            "event_data": {"amount": 10, "owner": "Eva", "destiny": None},
        }
    ]
    origen = entrada / "evento.json"
    origen.write_text(json.dumps(payload), encoding="utf-8")

    fake_gestion = MagicMock()
    instancia = MagicMock()
    fake_gestion.gestionDatos.return_value = instancia

    monkeypatch.setattr(daemonInput, "carpeta_tratados", str(tratados))
    monkeypatch.setattr(daemonInput, "carpeta_error", str(error))
    monkeypatch.setattr(daemonInput, "fichero", "evento.json")
    monkeypatch.setattr(daemonInput, "gestionDatos", fake_gestion)

    procesador = daemonInput.ProcesadoDatosDemonio()
    procesador.procesar_fichero(str(origen))

    instancia.ejecutarAccion.assert_called_once()
    assert (tratados / "evento.json").exists()
    assert not origen.exists()


def test_procesar_fichero_error_mueve_a_error(tmp_path, monkeypatch):
    entrada = tmp_path / "entrada"
    tratados = tmp_path / "tratados"
    error = tmp_path / "error"
    entrada.mkdir()
    tratados.mkdir()
    error.mkdir()

    origen = entrada / "roto.json"
    origen.write_text("{no-es-json", encoding="utf-8")

    monkeypatch.setattr(daemonInput, "carpeta_tratados", str(tratados))
    monkeypatch.setattr(daemonInput, "carpeta_error", str(error))
    monkeypatch.setattr(daemonInput, "fichero", "roto.json")

    procesador = daemonInput.ProcesadoDatosDemonio()
    procesador.procesar_fichero(str(origen))

    assert (error / "roto.json").exists()
    assert not (tratados / "roto.json").exists()


def test_handler_on_created_ignora_directorios(monkeypatch):
    llamado = {"ok": False}

    def fake_procesar(_self, _ruta):
        llamado["ok"] = True

    monkeypatch.setattr(daemonInput.ProcesadoDatosDemonio, "procesar_fichero", fake_procesar)

    evento = MagicMock()
    evento.is_directory = True
    evento.src_path = "/tmp/carpeta"
    daemonInput.MiHandler().on_created(evento)
    assert llamado["ok"] is False


def test_handler_on_created_procesa_fichero(monkeypatch):
    llamado = {"ruta": None}

    def fake_procesar(_self, ruta):
        llamado["ruta"] = ruta

    monkeypatch.setattr(daemonInput.ProcesadoDatosDemonio, "procesar_fichero", fake_procesar)

    evento = MagicMock()
    evento.is_directory = False
    evento.src_path = "/tmp/dato.json"
    daemonInput.MiHandler().on_created(evento)
    assert llamado["ruta"] == "/tmp/dato.json"


def test_rutas_de_carpetas_son_paths():
    assert Path(daemonInput.carpeta_entrada).name == "entrada"
    assert Path(daemonInput.carpeta_tratados).name == "tratados"
    assert Path(daemonInput.carpeta_error).name == "error"
