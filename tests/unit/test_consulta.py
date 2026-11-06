"""RN-01 inmutabilidad, enmiendas, urgencias (RN-02) y RN-04 bloqueo por alergia."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.domain.common import AlergiaBloqueoError, BusinessRuleViolation, NotaInmutableError, ValidationDomainError
from src.domain.consulta import (CedulaProfesional, Consulta, JustificacionClinica, MedicamentoDosificado)
from src.domain.paciente import Alergeno, Paciente, Peso
from src.domain.servicios import ServicioValidacionAlergias

pytestmark = pytest.mark.unit
AHORA = datetime(2026, 11, 6, 10, tzinfo=timezone.utc)
CED = "1234567"


def consulta_firmada():
    c = Consulta.abrir("C1", "P1", CED, AHORA)
    c.redactar_soap("s", "o", "a", "p")
    c.firmar_y_cerrar(CED, AHORA)
    return c


def paciente(alergia=None):
    p = Paciente.registrar("P1", "Rex", "PERRO", "T1", "EXP-1", date(2026, 11, 6), peso_kg="10")
    if alergia:
        p.registrar_alergia(Alergeno(alergia))
    return p


def med(pa="amoxicilina", peso=Peso("10")):
    return MedicamentoDosificado.para_peso(pa, "12.5", "oral", 12, 7, peso)


# ---------------- RN-01
def test_firmar_congela_y_registra_cedula():
    c = consulta_firmada()
    assert c.congelada and c.nota.firmada_por.numero == CED
    assert [e.name for e in c.pull_events()] == ["NotaSOAPFirmadaEvent"]


def test_nota_firmada_no_se_edita_ni_se_refirma_ni_se_receta():
    c = consulta_firmada()
    with pytest.raises(NotaInmutableError):
        c.redactar_soap("x", "x", "x", "x")
    with pytest.raises(NotaInmutableError):
        c.firmar_y_cerrar(CED)
    with pytest.raises(NotaInmutableError):
        c.agregar_a_receta(med())
    assert c.nota.subjetivo == "s"


def test_no_firma_nota_incompleta_ni_cedula_invalida():
    c = Consulta.abrir("C1", "P1", CED, AHORA)
    c.redactar_soap("s", "", "a", "p")
    with pytest.raises(ValidationDomainError):
        c.firmar_y_cerrar(CED)
    c.redactar_soap("s", "o", "a", "p")
    with pytest.raises(ValidationDomainError):
        c.firmar_y_cerrar("12")
    assert not c.congelada


def test_enmienda_solo_sobre_nota_firmada_y_conserva_original():
    c = Consulta.abrir("C1", "P1", CED, AHORA)
    c.redactar_soap("s", "o", "a", "p")
    with pytest.raises(BusinessRuleViolation):
        c.anexar_enmienda(CED, "motivo", "detalle")
    c.firmar_y_cerrar(CED, AHORA)
    e = c.anexar_enmienda("7654321", "error de dosis", "corregir", AHORA)
    assert c.nota.subjetivo == "s" and len(c.enmiendas) == 1 and e.cedula.numero == "7654321"
    with pytest.raises(ValidationDomainError):
        c.anexar_enmienda(CED, " ", "detalle")


# ---------------- RN-02
def test_urgencia_no_exige_datos_administrativos_y_es_rojo():
    c = Consulta.admitir_urgencia("C9", "atropellamiento", AHORA)
    assert c.paciente_id is None and c.triage.value == "ROJO"
    assert [e.name for e in c.pull_events()] == ["AdmisionUrgenciaActivadaEvent"]
    c.vincular_paciente("P1")
    with pytest.raises(BusinessRuleViolation):
        c.vincular_paciente("P2")
    with pytest.raises(ValidationDomainError):
        Consulta.admitir_urgencia("C", " ", AHORA)


# ---------------- RN-04
def test_dosis_calculada_por_peso_y_requiere_peso():
    assert med().dosis_calculada_mg == Decimal("125.00")
    with pytest.raises(ValidationDomainError):
        med(peso=None)
    with pytest.raises(ValidationDomainError):
        MedicamentoDosificado.para_peso("x", "0", "oral", 8, 3, Peso("5"))
    with pytest.raises(ValidationDomainError):
        MedicamentoDosificado.para_peso("x", "abc", "oral", 8, 3, Peso("5"))


def test_rn04_bloquea_alergeno_y_no_modifica_receta():
    c, p = Consulta.abrir("C1", "P1", CED, AHORA), paciente("Penicilina")
    with pytest.raises(AlergiaBloqueoError) as e:
        ServicioValidacionAlergias().prescribir(c, p, med("penicilina"))
    assert c.receta == [] and e.value.event.name == "BloqueoAlergiaDisparadoEvent"


def test_rn04_sin_alergia_prescribe():
    c, p = Consulta.abrir("C1", "P1", CED, AHORA), paciente("Penicilina")
    ServicioValidacionAlergias().prescribir(c, p, med("amoxicilina"))
    assert len(c.receta) == 1 and c.receta[0].justificacion is None


def test_rn04_excepcion_con_justificacion_bajo_cedula():
    c, p = Consulta.abrir("C1", "P1", CED, AHORA), paciente("penicilina")
    j = JustificacionClinica("beneficio supera riesgo, bajo monitoreo", CedulaProfesional(CED))
    ServicioValidacionAlergias().prescribir(c, p, med("PENICILINA"), j)
    assert c.receta[0].justificacion.texto.startswith("beneficio")
    assert "PrescripcionConAlergiaJustificadaEvent" in [e.name for e in c.pull_events()]
    with pytest.raises(ValidationDomainError):
        JustificacionClinica(" ", CedulaProfesional(CED))


# ---------------- US14 laboratorio
import hashlib  # noqa: E402

from src.domain.common import EntityNotFound  # noqa: E402


def test_us14_solicitar_y_adjuntar_resultado_emite_alerta_al_medico():
    c = Consulta.abrir("C1", "P1", CED, AHORA)
    e = c.solicitar_estudio("Hemograma completo", AHORA)
    assert e.estado == "PENDIENTE"
    huella = hashlib.sha256(b"pdf").hexdigest()
    c.adjuntar_resultado(e.id, "hemograma.PDF", huella, AHORA)
    assert e.estado == "RECIBIDO" and e.resultado.sha256 == huella
    ev = c.pull_events()
    assert [x.name for x in ev] == ["EstudioLaboratorioSolicitadoEvent", "ResultadoLaboratorioAdjuntadoEvent"]
    assert ev[1].cedula_medico == CED and ev[1].tipo_estudio == "Hemograma completo"


def test_us14_resultados_se_anexan_aun_con_nota_firmada():
    """RN-01 protege la nota; los anexos de laboratorio no la editan."""
    c = consulta_firmada()
    e = c.solicitar_estudio("Química sanguínea")
    c.adjuntar_resultado(e.id, "quimica.png")
    assert c.congelada and c.nota.subjetivo == "s"


@pytest.mark.parametrize("archivo,sha", [("virus.exe", None), ("sin_extension", None), (" ", None), ("ok.pdf", "xyz")])
def test_us14_archivo_o_hash_invalido(archivo, sha):
    c = Consulta.abrir("C1", "P1", CED, AHORA)
    e = c.solicitar_estudio("Hemograma")
    with pytest.raises(ValidationDomainError):
        c.adjuntar_resultado(e.id, archivo, sha)
    assert e.estado == "PENDIENTE"


def test_us14_reglas_de_estado():
    c = Consulta.abrir("C1", "P1", CED, AHORA)
    e = c.solicitar_estudio("Hemograma")
    c.adjuntar_resultado(e.id, "a.pdf")
    with pytest.raises(BusinessRuleViolation, match="ya tiene"):
        c.adjuntar_resultado(e.id, "b.pdf")
    with pytest.raises(EntityNotFound):
        c.adjuntar_resultado("LAB-NOEXISTE", "a.pdf")
    with pytest.raises(ValidationDomainError):
        c.solicitar_estudio(" ")
    urgencia = Consulta.admitir_urgencia("U1", "trauma", AHORA)
    with pytest.raises(BusinessRuleViolation, match="Regulariza"):
        urgencia.solicitar_estudio("Hemograma")
