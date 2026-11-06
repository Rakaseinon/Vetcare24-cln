"""US02 — Agenda inteligente: bloqueo por servicio, asignación de sala y prevención de solapamientos."""
from datetime import datetime, timedelta, timezone

import pytest

from src.domain.agenda import (Cita, EstadoCita, InicioFuturoSpec, Propuesta, SalaLibreSpec, ServicioAgenda,
                               TipoServicioAgenda as T, a_utc, duracion_para)
from src.domain.common import BusinessRuleViolation, InvalidStateTransition, ValidationDomainError

pytestmark = pytest.mark.unit
AHORA = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
LUNES = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)
svc = ServicioAgenda()


def agendar(tipo, inicio=LUNES, existentes=(), dur=None, id="C"):
    return svc.agendar(id, "P1", tipo, inicio, list(existentes), AHORA, dur)


@pytest.mark.parametrize("tipo,minutos", [(T.VACUNA, 15), (T.CONSULTA_GENERAL, 30), (T.ESPECIALIDAD, 45), (T.CIRUGIA, 90)])
def test_bloqueo_segun_servicio(tipo, minutos):
    c = agendar(tipo)
    assert c.duracion_min == minutos and c.fin - c.inicio == timedelta(minutes=minutos)


def test_cirugia_mayor_bloquea_90_y_asigna_quirofano():  # escenario Gherkin de US02
    c = agendar(T.CIRUGIA)
    assert c.duracion_min == 90 and c.sala.startswith("QUIR-")


@pytest.mark.parametrize("dur,ok", [(90, True), (105, True), (120, True), (89, False), (121, False)])
def test_cirugia_admite_90_a_120(dur, ok):
    if ok:
        assert duracion_para(T.CIRUGIA, dur) == dur
    else:
        with pytest.raises(ValidationDomainError):
            duracion_para(T.CIRUGIA, dur)


def test_otros_servicios_no_aceptan_duracion_personalizada():
    with pytest.raises(ValidationDomainError):
        duracion_para(T.CONSULTA_GENERAL, 60)


def test_dos_citas_solapadas_usan_salas_distintas_hasta_agotarlas():
    citas = []
    for i in range(3):  # 3 consultorios
        citas.append(agendar(T.CONSULTA_GENERAL, existentes=citas, id=f"C{i}"))
    assert {c.sala for c in citas} == {"CONS-01", "CONS-02", "CONS-03"}
    with pytest.raises(BusinessRuleViolation, match="No hay consultorio"):
        agendar(T.CONSULTA_GENERAL, existentes=citas)


def test_quirofanos_agotados_con_sobrecupo_evitado():
    citas = [agendar(T.CIRUGIA, existentes=[], id="Q1")]
    citas.append(agendar(T.CIRUGIA, existentes=citas, id="Q2"))
    assert {c.sala for c in citas} == {"QUIR-01", "QUIR-02"}
    with pytest.raises(BusinessRuleViolation, match="quirofano"):
        agendar(T.CIRUGIA, inicio=LUNES + timedelta(minutes=30), existentes=citas)


def test_citas_consecutivas_sin_hueco_no_se_solapan():
    primera = agendar(T.CONSULTA_GENERAL)
    segunda = agendar(T.CONSULTA_GENERAL, inicio=primera.fin, existentes=[primera])
    assert segunda.sala == primera.sala  # el borde final es exclusivo


def test_cancelar_libera_la_sala():
    c1 = agendar(T.CIRUGIA, id="Q1")
    c2 = agendar(T.CIRUGIA, existentes=[c1], id="Q2")
    c1.cancelar()
    assert c1.estado is EstadoCita.CANCELADA and not c1.activa
    c3 = agendar(T.CIRUGIA, existentes=[c1, c2], id="Q3")
    assert c3.sala == c1.sala
    assert [e.name for e in c1.pull_events()] == ["CitaProgramadaEvent", "CitaCanceladaEvent"]


def test_maquina_de_estados_de_cita():
    c = agendar(T.VACUNA)
    c.atender()
    for accion in (c.cancelar, c.atender):
        with pytest.raises(InvalidStateTransition):
            accion()


def test_no_se_agenda_en_el_pasado_y_zonas_se_normalizan():
    with pytest.raises(ValidationDomainError, match="pasado"):
        agendar(T.VACUNA, inicio=AHORA - timedelta(hours=2))
    naive = a_utc(datetime(2026, 11, 9, 9, 0))
    cdmx = a_utc(datetime(2026, 11, 9, 3, 0, tzinfo=timezone(timedelta(hours=-6))))
    assert naive == cdmx == LUNES


def test_specifications_componibles():
    existente = agendar(T.CONSULTA_GENERAL)
    mismo = Propuesta(existente.sala, existente.inicio, existente.fin, (existente,))
    otra_sala = Propuesta("CONS-03", existente.inicio, existente.fin, (existente,))
    futuro = InicioFuturoSpec(AHORA)
    assert not SalaLibreSpec().is_satisfied_by(mismo) and SalaLibreSpec().is_satisfied_by(otra_sala)
    combinada = SalaLibreSpec() & futuro
    assert combinada.is_satisfied_by(otra_sala) and combinada.reasons(mismo) == ["sala_libre_en_el_lapso"]
    assert (~SalaLibreSpec()).is_satisfied_by(mismo)


def test_programar_directo_registra_evento():
    c = Cita.programar("C9", "P1", T.ESPECIALIDAD, "CONS-02", LUNES)
    assert c.fin == LUNES + timedelta(minutes=45) and c.pull_events()[0].sala == "CONS-02"


@pytest.mark.parametrize("horas_antes,tardia", [(48, False), (4, False), (3.9, True), (0.5, True)])
def test_politica_de_cancelacion_4h(horas_antes, tardia):
    c = agendar(T.CONSULTA_GENERAL)
    c.cancelar(c.inicio - timedelta(hours=horas_antes))
    assert c.cancelacion_tardia is tardia and c.cancelada_en is not None
    assert c.pull_events()[-1].tardia is tardia


def test_cancelar_sin_hora_no_marca_tardia():
    c = agendar(T.VACUNA)
    c.cancelar()
    assert c.cancelacion_tardia is False and c.cancelada_en is None
