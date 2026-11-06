"""La regla de dependencia (SOLID-D, ADR-001) se verifica automáticamente: api → application → domain ← infrastructure."""
import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
PERMITIDO = {  # capa -> capas que NO puede importar
    "domain": {"application", "infrastructure", "api"},
    "application": {"infrastructure", "api"},
    "infrastructure": {"api"},
}


def _importaciones(archivo: Path) -> set[str]:
    capas = set()
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if nodo.level and nodo.level >= 2:  # `from ..capa import …` sale del paquete actual
                capas.add(modulo.split(".")[0])
            elif nodo.level == 0 and modulo.startswith("src."):
                capas.add(modulo.split(".")[1])
        elif isinstance(nodo, ast.Import):
            capas.update(a.name.split(".")[1] for a in nodo.names if a.name.startswith("src."))
    return capas


@pytest.mark.parametrize("capa,prohibidas", PERMITIDO.items())
def test_ninguna_capa_importa_hacia_afuera(capa, prohibidas):
    infractores = {f"{a.relative_to(SRC)} → {sorted(_importaciones(a) & prohibidas)}"
                   for a in (SRC / capa).rglob("*.py") if _importaciones(a) & prohibidas}
    assert not infractores, f"{capa} depende de capas externas: {infractores}"


def test_el_dominio_no_depende_de_frameworks_tecnicos():
    tecnicos = {"fastapi", "sqlalchemy", "pydantic", "starlette", "uvicorn"}
    for archivo in (SRC / "domain").rglob("*.py"):
        raices = set()
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                raices.add(nodo.module.split(".")[0])
            elif isinstance(nodo, ast.Import):
                raices.update(a.name.split(".")[0] for a in nodo.names)
        assert not (raices & tecnicos), f"{archivo.name} importa {raices & tecnicos}"


def test_la_aplicacion_acepta_cualquier_implementacion_de_los_puertos(reloj):
    """SOLID-L/D: un notificador y un bus distintos a los de producción reemplazan a los reales sin tocar servicios."""
    from src.api.container import build_container
    from src.infrastructure.config import Settings
    from tests.conftest import DATA_DIR

    class NotificadorMudo:
        enviados: list = []

        def enviar(self, canal, destino, mensaje):
            self.enviados.append((canal, destino, mensaje))

    c = build_container(Settings("sqlite://", True, DATA_DIR, "test"), clock=reloj)
    try:
        c.profilaxis.notificador = NotificadorMudo()
        assert c.profilaxis.procesar_recordatorios() is not None
    finally:
        c.engine.dispose()
