from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.container import build_container
from src.api.main import create_app
from src.infrastructure.config import Settings
from src.infrastructure.db import Base, make_engine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
AHORA = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)


class Reloj:
    """Reloj controlable para probar ventanas de 48 h / 4 h / 2 h sin dormir."""

    def __init__(self, t: datetime = AHORA) -> None:
        self.t = t

    def __call__(self) -> datetime:
        return self.t

    def avanzar(self, **kw) -> None:
        from datetime import timedelta
        self.t += timedelta(**kw)


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


def _settings() -> Settings:
    """SQLite en memoria por defecto; con TEST_DATABASE_URL (CI / compose) las mismas pruebas corren sobre PostgreSQL real."""
    url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    if not url.startswith("sqlite"):
        import src.infrastructure.models  # noqa: F401  (registra las tablas)
        e = make_engine(url)
        Base.metadata.drop_all(e)  # esquema limpio por prueba
        e.dispose()
    return Settings(url, True, DATA_DIR, "test")


@pytest.fixture
def container(reloj):
    c = build_container(_settings(), clock=reloj)
    yield c
    c.engine.dispose()


@pytest.fixture
def client(container):
    app = create_app(Settings("sqlite://", True, DATA_DIR, "test"), container=container)  # el contenedor ya trae su BD
    return TestClient(app)


def h(rol: str) -> dict:
    return {"X-Rol": rol}


RECEP, VET, ENF, DIR = h("RECEPCION"), h("VETERINARIO"), h("ENFERMERIA"), h("DIRECTOR")
CEDULA = "1234567"
