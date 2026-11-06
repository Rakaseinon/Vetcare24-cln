"""La semilla es idempotente y no depende de que no existan otros tutores."""
import pytest
from fastapi.testclient import TestClient

from src.api.container import build_container
from src.api.main import create_app
from src.infrastructure.config import Settings
from src.infrastructure.seed import sembrar_jaulas, sembrar_paquete_datos
from tests.conftest import DATA_DIR, RECEP

pytestmark = pytest.mark.integration


def test_sembrar_dos_veces_no_duplica_ni_reinicia_estados(container):
    r1 = sembrar_paquete_datos(container.uow_factory, DATA_DIR)
    assert r1 == {"tutores": 0, "servicios": 0, "ordenes": 0}  # el contenedor ya sembró al construirse
    assert sembrar_jaulas(container.uow_factory) == 0
    container.ordenes.transicionar("VET-O001", "aprobar")
    sembrar_paquete_datos(container.uow_factory, DATA_DIR)
    assert container.ordenes.obtener("VET-O001")["estado"] == "CONFIRMADA"  # no se reseteó


def test_tutor_registrado_antes_de_la_semilla_no_la_bloquea():
    c = build_container(Settings("sqlite://", False, DATA_DIR, "test"))
    try:
        client = TestClient(create_app(container=c))
        client.post("/tutores", json={"nombre": "Previo", "identificacion_oficial": "X", "email": "a@b.c"}, headers=RECEP)
        r = sembrar_paquete_datos(c.uow_factory, DATA_DIR)
        assert r == {"tutores": 41, "servicios": 20, "ordenes": 60}  # 40 del paquete + 1 registrado antes
        assert client.get("/ordenes/VET-O001", headers=RECEP).status_code == 200
    finally:
        c.engine.dispose()
