"""CitaAggregate (raíz: Cita) — Agenda inteligente (US02, RF-03).

Cada servicio bloquea una duración fija (BRD §3.1: 15 min vacuna, 30 consulta general, 45 especialidad,
90–120 quirófano) y exige un tipo de sala. Dos citas activas no pueden compartir sala en lapsos solapados.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from .common import (AggregateRoot, BusinessRuleViolation, Specification, StateMachine, ValidationDomainError)
from .events import CitaCanceladaEvent, CitaProgramadaEvent


class TipoServicioAgenda(str, Enum):
    VACUNA = "VACUNA"
    CONSULTA_GENERAL = "CONSULTA_GENERAL"
    ESPECIALIDAD = "ESPECIALIDAD"
    CIRUGIA = "CIRUGIA"


class TipoSala(str, Enum):
    CONSULTORIO = "CONSULTORIO"
    QUIROFANO = "QUIROFANO"


# Duración base (min) y tipo de sala por servicio.  La cirugía admite 90–120 min según complejidad.
DURACION_MIN: dict[TipoServicioAgenda, int] = {
    TipoServicioAgenda.VACUNA: 15, TipoServicioAgenda.CONSULTA_GENERAL: 30,
    TipoServicioAgenda.ESPECIALIDAD: 45, TipoServicioAgenda.CIRUGIA: 90}
SALA_REQUERIDA: dict[TipoServicioAgenda, TipoSala] = {
    TipoServicioAgenda.VACUNA: TipoSala.CONSULTORIO, TipoServicioAgenda.CONSULTA_GENERAL: TipoSala.CONSULTORIO,
    TipoServicioAgenda.ESPECIALIDAD: TipoSala.CONSULTORIO, TipoServicioAgenda.CIRUGIA: TipoSala.QUIROFANO}
SALAS: dict[TipoSala, tuple[str, ...]] = {
    TipoSala.CONSULTORIO: ("CONS-01", "CONS-02", "CONS-03"), TipoSala.QUIROFANO: ("QUIR-01", "QUIR-02")}
CIRUGIA_MIN, CIRUGIA_MAX = 90, 120
AVISO_MINIMO_CANCELACION = timedelta(hours=4)  # levantamiento: sin penalización avisando con ≥ 4 h


class EstadoCita(str, Enum):
    PROGRAMADA = "PROGRAMADA"
    ATENDIDA = "ATENDIDA"
    CANCELADA = "CANCELADA"


MAQUINA_CITA: StateMachine[EstadoCita] = StateMachine("Cita", [
    (EstadoCita.PROGRAMADA, "atender", EstadoCita.ATENDIDA),
    (EstadoCita.PROGRAMADA, "cancelar", EstadoCita.CANCELADA),
])


def a_utc(dt: datetime) -> datetime:
    """Fechas sin zona se interpretan como UTC; con zona se convierten a UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def duracion_para(tipo: TipoServicioAgenda, duracion_min: int | None = None) -> int:
    if duracion_min is None:
        return DURACION_MIN[tipo]
    if tipo is not TipoServicioAgenda.CIRUGIA:
        raise ValidationDomainError("Solo la cirugía admite duración personalizada (90–120 min)")
    if not CIRUGIA_MIN <= duracion_min <= CIRUGIA_MAX:
        raise ValidationDomainError(f"La cirugía bloquea entre {CIRUGIA_MIN} y {CIRUGIA_MAX} minutos")
    return duracion_min


@dataclass
class Cita(AggregateRoot):
    id: str
    paciente_id: str
    tipo: TipoServicioAgenda
    sala: str
    inicio: datetime
    fin: datetime
    estado: EstadoCita = EstadoCita.PROGRAMADA
    cancelada_en: datetime | None = None
    cancelacion_tardia: bool = False

    @classmethod
    def programar(cls, id: str, paciente_id: str, tipo: TipoServicioAgenda, sala: str, inicio: datetime,
                  duracion_min: int | None = None) -> "Cita":
        ini = a_utc(inicio)
        c = cls(id=id, paciente_id=paciente_id, tipo=tipo, sala=sala, inicio=ini,
                fin=ini + timedelta(minutes=duracion_para(tipo, duracion_min)))
        c._record(CitaProgramadaEvent(cita_id=id, paciente_id=paciente_id, sala=sala, inicio=ini))
        return c

    @property
    def duracion_min(self) -> int:
        return int((self.fin - self.inicio).total_seconds() // 60)

    @property
    def activa(self) -> bool:
        return self.estado is EstadoCita.PROGRAMADA

    def se_solapa_con(self, ini: datetime, fin: datetime) -> bool:
        return self.inicio < fin and ini < self.fin

    def cancelar(self, ahora: datetime | None = None) -> None:
        """Libera la sala. Con menos de 4 h de aviso la cancelación se marca «tardía» (KPI de citas no cumplidas)."""
        self.estado = MAQUINA_CITA.fire(self.estado, "cancelar")
        if ahora is not None:
            self.cancelada_en = a_utc(ahora)
            self.cancelacion_tardia = self.inicio - self.cancelada_en < AVISO_MINIMO_CANCELACION
        self._record(CitaCanceladaEvent(cita_id=self.id, sala=self.sala, tardia=self.cancelacion_tardia))

    def atender(self) -> None:
        self.estado = MAQUINA_CITA.fire(self.estado, "atender")


# ------------------------------------------------------------------ Specifications de agenda
@dataclass(frozen=True)
class Propuesta:
    """Candidato a reservar: sala + lapso, contra las citas ya existentes."""
    sala: str
    inicio: datetime
    fin: datetime
    existentes: tuple[Cita, ...] = field(default_factory=tuple)


class SalaLibreSpec(Specification[Propuesta]):
    nombre = "sala_libre_en_el_lapso"

    def is_satisfied_by(self, p: Propuesta) -> bool:
        return not any(c.activa and c.sala == p.sala and c.se_solapa_con(p.inicio, p.fin) for c in p.existentes)


class InicioFuturoSpec(Specification[Propuesta]):
    """No se agenda en el pasado (con tolerancia de un minuto por latencia de captura)."""
    nombre = "inicio_no_pasado"

    def __init__(self, ahora: datetime) -> None:
        self.ahora = a_utc(ahora)

    def is_satisfied_by(self, p: Propuesta) -> bool:
        return p.inicio >= self.ahora - timedelta(minutes=1)


class ServicioAgenda:
    """Servicio de dominio: elige la primera sala compatible y libre (US02: «asigna quirófano disponible»)."""

    @staticmethod
    def ventana(tipo: TipoServicioAgenda, inicio: datetime, duracion_min: int | None = None) -> tuple[datetime, datetime]:
        """Lapso [inicio, fin) que bloquea el servicio; el servicio de aplicación lo usa para cargar solo citas relevantes."""
        ini = a_utc(inicio)
        return ini, ini + timedelta(minutes=duracion_para(tipo, duracion_min))

    def agendar(self, id: str, paciente_id: str, tipo: TipoServicioAgenda, inicio: datetime,
                existentes: list[Cita], ahora: datetime, duracion_min: int | None = None) -> Cita:
        ini, fin = self.ventana(tipo, inicio, duracion_min)
        tipo_sala = SALA_REQUERIDA[tipo]
        if not InicioFuturoSpec(ahora).is_satisfied_by(Propuesta("", ini, fin)):
            raise ValidationDomainError("No se puede agendar una cita en el pasado")
        for sala in SALAS[tipo_sala]:
            if SalaLibreSpec().is_satisfied_by(Propuesta(sala, ini, fin, tuple(existentes))):
                return Cita.programar(id, paciente_id, tipo, sala, ini, duracion_min)
        raise BusinessRuleViolation(
            f"No hay {tipo_sala.value.lower()} disponible de {ini:%H:%M} a {fin:%H:%M} UTC; "
            f"elige otro horario (sobrecupo evitado, US02)")
