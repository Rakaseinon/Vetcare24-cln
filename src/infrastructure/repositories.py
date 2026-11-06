"""Repositorios SQLAlchemy: un agregado = una fila (columnas indexadas + documento JSON)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain.agenda import Cita, EstadoCita
from ..domain.common import AggregateRoot
from ..domain.consulta import Consulta
from ..domain.hospitalizacion import EstadoHospitalizacion, Hospitalizacion, Jaula
from ..domain.orden_servicio import OrdenServicio, ServicioCatalogo
from ..domain.paciente import Paciente
from ..domain.profilaxis import RegistroVacuna
from ..domain.specifications import VENTANA_RECORDATORIO_DIAS
from ..domain.tutor import Tutor
from . import models as m
from .codec import decode, encode

A = TypeVar("A", bound=AggregateRoot)


class DocRepository(Generic[A]):
    row: type

    def __init__(self, session: Session, track: Callable[[AggregateRoot], None]) -> None:
        self.session, self._track = session, track

    def _cols(self, agg: A) -> dict:
        return {}

    def save(self, agg: A) -> None:
        self.session.merge(self.row(id=agg.id, doc=encode(agg), **self._cols(agg)))
        self.session.flush()
        self._track(agg)

    def get(self, id: str) -> A | None:
        r = self.session.get(self.row, id)
        return decode(r.doc) if r else None

    def _all(self, stmt: Any) -> list[A]:
        return [decode(r.doc) for r in self.session.scalars(stmt)]

    def list_all(self) -> list[A]:
        return self._all(select(self.row).order_by(self.row.id))

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.row)) or 0


class TutorRepository(DocRepository[Tutor]):
    row = m.TutorRow

    def _cols(self, t: Tutor) -> dict:
        return {"nombre": t.nombre, "telefono": t.telefono}

    def buscar(self, q: str) -> list[Tutor]:
        like = f"%{q}%"
        return self._all(select(m.TutorRow).where((m.TutorRow.nombre.ilike(like)) | (m.TutorRow.telefono == q)))


class ServicioRepository(DocRepository[ServicioCatalogo]):
    row = m.ServicioRow


class PacienteRepository(DocRepository[Paciente]):
    row = m.PacienteRow

    def _cols(self, p: Paciente) -> dict:
        return {"tutor_id": p.tutor_id, "nombre": p.nombre, "codigo_expediente": p.codigo_expediente,
                "microchip": p.microchip.codigo if p.microchip else None}

    def siguiente_codigo(self) -> str:
        return f"EXP-{self.count() + 1:06d}"

    def por_microchip(self, codigo: str) -> Paciente | None:
        r = self.session.scalar(select(m.PacienteRow).where(m.PacienteRow.microchip == codigo.strip().upper()))
        return decode(r.doc) if r else None

    def buscar(self, q: str, tutor_ids: list[str]) -> list[Paciente]:
        like = f"%{q}%"
        cond = (m.PacienteRow.nombre.ilike(like)) | (m.PacienteRow.microchip == q.strip().upper()) | \
               (m.PacienteRow.codigo_expediente == q.strip().upper())
        if tutor_ids:
            cond = cond | m.PacienteRow.tutor_id.in_(tutor_ids)
        return self._all(select(m.PacienteRow).where(cond).order_by(m.PacienteRow.id))


class ConsultaRepository(DocRepository[Consulta]):
    row = m.ConsultaRow

    def _cols(self, c: Consulta) -> dict:
        return {"paciente_id": c.paciente_id}

    def de_paciente(self, paciente_id: str) -> list[Consulta]:
        return self._all(select(m.ConsultaRow).where(m.ConsultaRow.paciente_id == paciente_id))


class HospitalizacionRepository(DocRepository[Hospitalizacion]):
    row = m.HospitalizacionRow

    def _cols(self, h: Hospitalizacion) -> dict:
        return {"paciente_id": h.paciente_id, "estado": h.estado.value}

    def activa_de(self, paciente_id: str) -> Hospitalizacion | None:
        r = self.session.scalar(select(m.HospitalizacionRow).where(
            m.HospitalizacionRow.paciente_id == paciente_id,
            m.HospitalizacionRow.estado != EstadoHospitalizacion.EGRESADO.value))
        return decode(r.doc) if r else None

    def activas(self) -> list[Hospitalizacion]:
        return self._all(select(m.HospitalizacionRow).where(
            m.HospitalizacionRow.estado != EstadoHospitalizacion.EGRESADO.value))

    def de_paciente(self, paciente_id: str) -> list[Hospitalizacion]:
        return self._all(select(m.HospitalizacionRow).where(m.HospitalizacionRow.paciente_id == paciente_id))


class JaulaRepository(DocRepository[Jaula]):
    row = m.JaulaRow

    def _cols(self, j: Jaula) -> dict:
        return {"tipo": j.tipo.value, "ocupada": not j.libre}

    def listar(self, solo_libres: bool = False) -> list[Jaula]:
        stmt = select(m.JaulaRow).order_by(m.JaulaRow.id)
        if solo_libres:
            stmt = stmt.where(m.JaulaRow.ocupada.is_(False))
        return self._all(stmt)


class VacunaRepository(DocRepository[RegistroVacuna]):
    row = m.VacunaRow

    def _cols(self, r: RegistroVacuna) -> dict:
        return {"paciente_id": r.paciente_id, "fecha_aplicacion": r.fecha_aplicacion,
                "fecha_refuerzo": r.programacion.fecha_programada, "notificado": r.programacion.notificado}

    def de_paciente(self, paciente_id: str) -> list[RegistroVacuna]:
        return self._all(select(m.VacunaRow).where(m.VacunaRow.paciente_id == paciente_id))

    def candidatos_recordatorio(self, hoy: date) -> list[RegistroVacuna]:
        return self._all(select(m.VacunaRow).where(
            m.VacunaRow.notificado.is_(False), m.VacunaRow.fecha_refuerzo >= hoy,
            m.VacunaRow.fecha_refuerzo <= hoy + timedelta(days=VENTANA_RECORDATORIO_DIAS)))

    def aplicadas_entre(self, desde: date, hasta: date) -> int:
        return self.session.scalar(select(func.count()).select_from(m.VacunaRow).where(
            m.VacunaRow.fecha_aplicacion >= desde, m.VacunaRow.fecha_aplicacion <= hasta)) or 0

    def refuerzos_pendientes(self, hoy: date) -> int:
        return self.session.scalar(select(func.count()).select_from(m.VacunaRow).where(
            m.VacunaRow.fecha_refuerzo >= hoy, m.VacunaRow.notificado.is_(False))) or 0


class OrdenRepository(DocRepository[OrdenServicio]):
    row = m.OrdenRow

    def _cols(self, o: OrdenServicio) -> dict:
        return {"tutor_id": o.tutor_id, "estado": o.estado.value, "fecha_solicitud": o.fecha_solicitud}

    def de_tutor(self, tutor_id: str) -> list[OrdenServicio]:
        return self._all(select(m.OrdenRow).where(m.OrdenRow.tutor_id == tutor_id))

    def contar_por_estado(self, estado: str, desde: date, hasta: date) -> int:
        return self.session.scalar(select(func.count()).select_from(m.OrdenRow).where(
            m.OrdenRow.estado == estado, m.OrdenRow.fecha_solicitud >= desde,
            m.OrdenRow.fecha_solicitud <= hasta)) or 0


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


class CitaRepository(DocRepository[Cita]):
    row = m.CitaRow

    def _cols(self, c: Cita) -> dict:
        return {"paciente_id": c.paciente_id, "sala": c.sala, "estado": c.estado.value,
                "inicio": _naive_utc(c.inicio), "fin": _naive_utc(c.fin)}

    def activas_en(self, inicio: datetime, fin: datetime) -> list[Cita]:
        """Citas PROGRAMADAS cuyo lapso se cruza con [inicio, fin)."""
        return self._all(select(m.CitaRow).where(
            m.CitaRow.estado == EstadoCita.PROGRAMADA.value,
            m.CitaRow.inicio < _naive_utc(fin), m.CitaRow.fin > _naive_utc(inicio)))

    def canceladas_entre(self, desde: date, hasta: date) -> list[Cita]:
        return self._all(select(m.CitaRow).where(
            m.CitaRow.estado == EstadoCita.CANCELADA.value,
            m.CitaRow.inicio >= datetime(desde.year, desde.month, desde.day),
            m.CitaRow.inicio < datetime(hasta.year, hasta.month, hasta.day) + timedelta(days=1)))

    def del_dia(self, dia: date) -> list[Cita]:
        ini = datetime(dia.year, dia.month, dia.day)
        return self._all(select(m.CitaRow).where(m.CitaRow.inicio >= ini, m.CitaRow.inicio < ini + timedelta(days=1))
                         .order_by(m.CitaRow.inicio))
