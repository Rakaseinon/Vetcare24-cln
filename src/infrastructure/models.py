"""Tablas: una por agregado raíz. Columnas indexadas para consulta + documento JSON del agregado (ADR-003)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

DOC = JSON().with_variant(JSONB(), "postgresql")


class TutorRow(Base):
    __tablename__ = "tutores"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), index=True)
    telefono: Mapped[str | None] = mapped_column(String(30), index=True, nullable=True)
    doc: Mapped[dict] = mapped_column(DOC)


class ServicioRow(Base):
    __tablename__ = "servicios"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    doc: Mapped[dict] = mapped_column(DOC)


class PacienteRow(Base):
    __tablename__ = "pacientes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tutor_id: Mapped[str] = mapped_column(String(40), index=True)
    nombre: Mapped[str] = mapped_column(String(200), index=True)
    codigo_expediente: Mapped[str] = mapped_column(String(20), unique=True)
    microchip: Mapped[str | None] = mapped_column(String(15), unique=True, nullable=True)
    doc: Mapped[dict] = mapped_column(DOC)


class ConsultaRow(Base):
    __tablename__ = "consultas"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    paciente_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    doc: Mapped[dict] = mapped_column(DOC)


class HospitalizacionRow(Base):
    __tablename__ = "hospitalizaciones"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    paciente_id: Mapped[str] = mapped_column(String(40), index=True)
    estado: Mapped[str] = mapped_column(String(40), index=True)
    doc: Mapped[dict] = mapped_column(DOC)


class JaulaRow(Base):
    __tablename__ = "jaulas"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    ocupada: Mapped[bool] = mapped_column(Boolean, index=True)
    doc: Mapped[dict] = mapped_column(DOC)


class VacunaRow(Base):
    __tablename__ = "registros_vacuna"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    paciente_id: Mapped[str] = mapped_column(String(40), index=True)
    fecha_aplicacion: Mapped[date] = mapped_column(Date, index=True)
    fecha_refuerzo: Mapped[date] = mapped_column(Date, index=True)
    notificado: Mapped[bool] = mapped_column(Boolean, index=True)
    doc: Mapped[dict] = mapped_column(DOC)


class OrdenRow(Base):
    __tablename__ = "ordenes_servicio"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tutor_id: Mapped[str] = mapped_column(String(40), index=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    fecha_solicitud: Mapped[date] = mapped_column(Date, index=True)
    doc: Mapped[dict] = mapped_column(DOC)


class CitaRow(Base):
    __tablename__ = "citas"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    paciente_id: Mapped[str] = mapped_column(String(40), index=True)
    sala: Mapped[str] = mapped_column(String(20), index=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    inicio: Mapped[datetime] = mapped_column(DateTime, index=True)  # UTC sin zona (comparable en SQLite y PostgreSQL)
    fin: Mapped[datetime] = mapped_column(DateTime)
    doc: Mapped[dict] = mapped_column(DOC)
