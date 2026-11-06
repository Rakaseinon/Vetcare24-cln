import pytest

from src.infrastructure.config import Settings
from src.infrastructure.db import normalizar_url

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("entrada,salida", [
    ("postgres://u:p@h:5432/d", "postgresql+psycopg2://u:p@h:5432/d"),
    ("postgresql://u:p@h/d", "postgresql+psycopg2://u:p@h/d"),
    ("postgresql+psycopg2://u:p@h/d", "postgresql+psycopg2://u:p@h/d"),
    ("sqlite:///./x.db", "sqlite:///./x.db")])
def test_normalizar_url(entrada, salida):
    assert normalizar_url(entrada) == salida


def test_settings_desde_entorno(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@h/d")
    monkeypatch.setenv("SEED_ON_START", "TRUE")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENVIRONMENT", "production")
    s = Settings.from_env()
    assert (s.database_url, s.seed_on_start, s.data_dir, s.environment) == ("postgres://u:p@h/d", True, tmp_path, "production")


def test_settings_defaults(monkeypatch):
    for k in ("DATABASE_URL", "SEED_ON_START", "DATA_DIR", "ENVIRONMENT"):
        monkeypatch.delenv(k, raising=False)
    s = Settings.from_env()
    assert s.database_url.startswith("sqlite") and s.seed_on_start is False and s.environment == "development"
