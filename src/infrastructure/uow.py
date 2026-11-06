"""UnitOfWork SQLAlchemy: transacción atómica + publicación de eventos de dominio solo tras el commit."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ..domain.common import AggregateRoot
from .repositories import (CitaRepository, ConsultaRepository, HospitalizacionRepository, JaulaRepository, OrdenRepository,
                           PacienteRepository, ServicioRepository, TutorRepository, VacunaRepository)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session], bus: Any) -> None:
        self._factory, self._bus = session_factory, bus
        self._seen: list[AggregateRoot] = []

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._factory()
        self._seen = []
        t = self._track
        self.tutores = TutorRepository(self.session, t)
        self.servicios = ServicioRepository(self.session, t)
        self.pacientes = PacienteRepository(self.session, t)
        self.consultas = ConsultaRepository(self.session, t)
        self.hospitalizaciones = HospitalizacionRepository(self.session, t)
        self.jaulas = JaulaRepository(self.session, t)
        self.vacunas = VacunaRepository(self.session, t)
        self.ordenes = OrdenRepository(self.session, t)
        self.citas = CitaRepository(self.session, t)
        return self

    def _track(self, agg: AggregateRoot) -> None:
        if not any(a is agg for a in self._seen):
            self._seen.append(agg)

    def commit(self) -> None:
        self.session.commit()
        eventos = [e for agg in self._seen for e in agg.pull_events()]
        self._seen = []
        self._bus.publish_all(eventos)  # solo después de persistir con éxito

    def rollback(self) -> None:
        self.session.rollback()
        self._seen = []

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.rollback()
        self.session.close()
