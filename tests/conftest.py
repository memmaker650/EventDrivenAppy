import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Usa un SQLite temporal para no tocar events.db de desarrollo."""
    db_file = tmp_path / "events.db"

    def _get_connection():
        return sqlite3.connect(str(db_file))

    monkeypatch.setattr(database, "get_connection", _get_connection)
    database.init_db()
    database.create_hipotecasTable()
    database.create_amortizaciones_anticipadasTable()
    return db_file


class FakeApp:
    def __init__(self):
        self.estados = []

    def actualizar_estado(self, mensaje, tipo):
        self.estados.append((mensaje, tipo))


@pytest.fixture
def fake_app():
    return FakeApp()
