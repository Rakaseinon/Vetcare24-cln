from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.domain.common import BusinessRuleViolation, ValidationDomainError
from src.domain.paciente import Alergeno, MicrochipCode, Paciente, Peso
from src.domain.tutor import Tutor

pytestmark = pytest.mark.unit
HOY = date(2026, 11, 6)
AHORA = datetime(2026, 11, 6, 10, tzinfo=timezone.utc)


def pac(**kw):
    base = dict(id="P1", nombre="Rex", especie="perro", tutor_id="T1", codigo_expediente="EXP-000001", hoy=HOY,
                peso_kg="12.5", fecha_nacimiento=date(2025, 1, 15), microchip="abc123456789")
    base.update(kw)
    return Paciente.registrar(**base)


def test_tutor_requiere_contacto_y_canal_valido():
    t = Tutor.registrar("T1", " Ana ", "INE123", telefono="811", canal_preferido="whatsapp")
    assert t.nombre == "Ana" and t.canal_preferido == "WHATSAPP"
    with pytest.raises(ValidationDomainError):
        Tutor.registrar("T2", "Ana", "INE")
    with pytest.raises(ValidationDomainError):
        Tutor.registrar("T2", "Ana", "INE", email="a@b.c", canal_preferido="SMS")
    with pytest.raises(ValidationDomainError):
        Tutor.registrar("T2", "  ", "INE", email="a@b.c")


def test_registro_paciente_normaliza_y_emite_evento():
    p = pac()
    assert p.especie == "PERRO" and p.microchip.codigo == "ABC123456789" and p.titularidad[0].tutor_id == "T1"
    assert [e.name for e in p.pull_events()] == ["PacienteRegistradoEvent"]


@pytest.mark.parametrize("kw", [dict(especie="dragon"), dict(fecha_nacimiento=date(2027, 1, 1)),
                                dict(peso_kg="0"), dict(peso_kg="abc"), dict(microchip="12"), dict(nombre=" ")])
def test_registro_invalido(kw):
    with pytest.raises(ValidationDomainError):
        pac(**kw)


def test_edad_en_meses():
    assert pac().edad_meses(HOY) == 21
    assert pac(fecha_nacimiento=None).edad_meses(HOY) is None
    assert pac(fecha_nacimiento=date(2026, 10, 20)).edad_meses(HOY) == 0


def test_alergias_sin_duplicados_y_alerta():
    p = pac()
    assert not p.alerta_alergia
    assert p.registrar_alergia(Alergeno("Penicilina")) is True
    assert p.registrar_alergia(Alergeno(" penicilina ")) is False
    assert p.alerta_alergia and p.tiene_alergia_a("PENICILINA") and not p.tiene_alergia_a("amoxicilina")
    assert [e.name for e in p.pull_events()].count("AlergiaDetectadaEvent") == 1


def test_triaje_actualiza_peso_y_alergias():
    p = pac()
    p.registrar_triaje(AHORA, Peso("13.2"), "38.6", "vómito", ["Penicilina"])
    assert p.peso.valor_kg == Decimal("13.2") and p.alerta_alergia and len(p.triajes) == 1
    with pytest.raises(ValidationDomainError):
        p.registrar_triaje(AHORA, Peso("13"), "55", "x")
    with pytest.raises(ValidationDomainError):
        p.registrar_triaje(AHORA, Peso("13"), "caliente", "x")


def test_rn05_transferencia_conserva_historial_y_cierra_titularidad():
    p = pac()
    p.registrar_alergia(Alergeno("penicilina"))
    p.transferir_a("T2", date(2026, 11, 7))
    assert p.tutor_id == "T2" and p.alergenos and p.codigo_expediente == "EXP-000001"
    assert p.titularidad[0].hasta == date(2026, 11, 7) and p.titularidad[1].hasta is None
    with pytest.raises(BusinessRuleViolation):
        p.transferir_a("T2", HOY)
    assert "TutorReasignadoEvent" in [e.name for e in p.pull_events()]


def test_value_objects_inmutables_y_validados():
    with pytest.raises(Exception):
        Peso("5").valor_kg = Decimal("6")  # frozen
    assert MicrochipCode("abcdefghi").codigo == "ABCDEFGHI"
    with pytest.raises(ValidationDomainError):
        Peso("201")


def test_tutor_inactivo_no_asume_responsabilidades():
    t = Tutor.registrar("T1", "Ana", "INE", email="a@b.c")
    t.asegurar_activo("registrar mascotas")
    t.activo = False
    with pytest.raises(BusinessRuleViolation, match="inactivo"):
        t.asegurar_activo("registrar mascotas")
