"""RN-03 trazabilidad y cálculo automático del refuerzo (21/28/365 días)."""
from datetime import date

import pytest

from src.domain.common import ValidationDomainError
from src.domain.profilaxis import EsquemaRefuerzo, IntervaloRefuerzo, RegistroVacuna

pytestmark = pytest.mark.unit
HOY = date(2026, 11, 6)


def aplicar(lote="L-9", marca="Zoetis", intervalo=IntervaloRefuerzo(21), fecha=HOY):
    return RegistroVacuna.aplicar("V1", "P1", "Quíntuple Canina", lote, marca, fecha, HOY, intervalo)


@pytest.mark.parametrize("dias", [21, 28, 365])
def test_refuerzo_exacto(dias):
    r = aplicar(intervalo=IntervaloRefuerzo(dias))
    assert (r.programacion.fecha_programada - HOY).days == dias


@pytest.mark.parametrize("lote,marca", [(None, "Zoetis"), ("", "Zoetis"), ("  ", "x"), ("L1", None), ("L1", "")])
def test_rn03_sin_lote_o_marca_no_se_registra(lote, marca):
    with pytest.raises(ValidationDomainError):
        aplicar(lote=lote, marca=marca)


def test_fecha_futura_invalida_y_eventos():
    with pytest.raises(ValidationDomainError):
        aplicar(fecha=date(2026, 12, 1))
    r = aplicar()
    assert [e.name for e in r.pull_events()] == ["VacunaAplicadaEvent", "RefuerzoProfilacticoCalculadoEvent"]
    assert r.lote.codigo == "L-9"


def test_intervalo_por_edad_y_esquema():
    assert IntervaloRefuerzo.para(3).dias == 21
    assert IntervaloRefuerzo.para(24).dias == 365
    assert IntervaloRefuerzo.para(None).dias == 365
    assert IntervaloRefuerzo.para(30, EsquemaRefuerzo.CACHORRO_28).dias == 28
    assert IntervaloRefuerzo.para(1, EsquemaRefuerzo.ANUAL).dias == 365
