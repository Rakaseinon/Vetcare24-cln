"""Eventos de dominio de VetCare 24 (nombres alineados con ADR-001 / diagrama de clases)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .common import DomainEvent


# --- PacienteAggregate
@dataclass(frozen=True, kw_only=True)
class PacienteRegistradoEvent(DomainEvent):
    paciente_id: str
    tutor_id: str


@dataclass(frozen=True, kw_only=True)
class AlergiaDetectadaEvent(DomainEvent):
    paciente_id: str
    principio_activo: str


@dataclass(frozen=True, kw_only=True)
class TutorReasignadoEvent(DomainEvent):  # RN-05
    paciente_id: str
    tutor_anterior: str
    tutor_nuevo: str


# --- ConsultaAggregate
@dataclass(frozen=True, kw_only=True)
class AdmisionUrgenciaActivadaEvent(DomainEvent):  # RN-02 (Código Rojo)
    consulta_id: str
    descripcion: str


@dataclass(frozen=True, kw_only=True)
class NotaSOAPFirmadaEvent(DomainEvent):  # RN-01
    consulta_id: str
    cedula: str


@dataclass(frozen=True, kw_only=True)
class NotaEnmiendaAnexadaEvent(DomainEvent):  # RN-01
    consulta_id: str
    enmienda_id: str
    cedula: str


@dataclass(frozen=True, kw_only=True)
class BloqueoAlergiaDisparadoEvent(DomainEvent):  # RN-04
    paciente_id: str
    principio_activo: str
    consulta_id: str


@dataclass(frozen=True, kw_only=True)
class PrescripcionConAlergiaJustificadaEvent(DomainEvent):  # RN-04 (excepción con cédula)
    consulta_id: str
    principio_activo: str
    cedula: str


# --- HospitalizacionAggregate
@dataclass(frozen=True, kw_only=True)
class PacienteHospitalizadoEvent(DomainEvent):
    hospitalizacion_id: str
    paciente_id: str
    jaula_id: str


@dataclass(frozen=True, kw_only=True)
class SignosVitalesFueraDeRangoEvent(DomainEvent):
    hospitalizacion_id: str
    alertas: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class AltaMedicaAutorizadaEvent(DomainEvent):  # RN-06
    hospitalizacion_id: str
    cedula: str


@dataclass(frozen=True, kw_only=True)
class CuentaLiquidadaEvent(DomainEvent):  # RN-06
    hospitalizacion_id: str


@dataclass(frozen=True, kw_only=True)
class JaulaLiberadaEvent(DomainEvent):  # RN-06
    jaula_id: str
    hospitalizacion_id: str


# --- ProfilaxisAggregate
@dataclass(frozen=True, kw_only=True)
class VacunaAplicadaEvent(DomainEvent):  # RN-03
    registro_id: str
    paciente_id: str
    lote: str


@dataclass(frozen=True, kw_only=True)
class RefuerzoProfilacticoCalculadoEvent(DomainEvent):
    registro_id: str
    fecha_refuerzo: date


@dataclass(frozen=True, kw_only=True)
class NotificacionRecordatorioDespachadaEvent(DomainEvent):
    registro_id: str
    canal: str


# --- OrdenServicio (US02)
@dataclass(frozen=True, kw_only=True)
class OrdenConfirmadaEvent(DomainEvent):
    orden_id: str


@dataclass(frozen=True, kw_only=True)
class OrdenRealizadaEvent(DomainEvent):
    orden_id: str


@dataclass(frozen=True, kw_only=True)
class OrdenCanceladaEvent(DomainEvent):
    orden_id: str


# --- Agenda (US02)
@dataclass(frozen=True, kw_only=True)
class CitaProgramadaEvent(DomainEvent):
    cita_id: str
    paciente_id: str
    sala: str
    inicio: datetime


@dataclass(frozen=True, kw_only=True)
class CitaCanceladaEvent(DomainEvent):
    cita_id: str
    sala: str
    tardia: bool = False


# --- Laboratorio (US14)
@dataclass(frozen=True, kw_only=True)
class EstudioLaboratorioSolicitadoEvent(DomainEvent):
    consulta_id: str
    estudio_id: str
    tipo_estudio: str


@dataclass(frozen=True, kw_only=True)
class ResultadoLaboratorioAdjuntadoEvent(DomainEvent):
    consulta_id: str
    estudio_id: str
    paciente_id: str | None
    cedula_medico: str | None
    tipo_estudio: str
