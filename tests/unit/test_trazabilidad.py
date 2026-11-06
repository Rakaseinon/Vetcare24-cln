"""La matriz de trazabilidad no puede mentir: cada referencia existe y el .md está generado desde la tabla."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import generar_trazabilidad as gt  # noqa: E402

pytestmark = pytest.mark.unit


def test_todas_las_referencias_existen():
    assert gt.referencias_rotas() == []


def test_detecta_referencias_falsas():
    assert gt.verificar_referencia("src/domain/consulta.py::NoExiste")
    assert gt.verificar_referencia("src/no_existe.py::X")
    assert gt.verificar_referencia("src/domain/consulta.py::Consulta") is None


def test_documento_esta_al_dia():
    actual = (gt.ROOT / "docs" / "TRAZABILIDAD.md").read_text(encoding="utf-8")
    assert actual == gt.render(), "Ejecuta: python scripts/generar_trazabilidad.py"


def test_cubre_las_15_user_stories_y_las_6_reglas_de_negocio():
    ids = " ".join(f[0] for f in gt.FILAS)
    for n in range(1, 16):
        assert f"US{n:02d}" in ids, f"falta US{n:02d}"
    for n in range(1, 7):
        assert f"RN-0{n}" in ids, f"falta RN-0{n}"


def test_cada_fila_de_requerimiento_tiene_al_menos_una_prueba():
    sin = [f[0] for f in gt.FILAS if not f[6]]
    assert sin == []
