"""Raíz de composición: ensambla infraestructura + servicios de aplicación."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..application.services import (AgendaService, ConsultaService, HospitalizacionService, OrdenService, PacienteService,
                                    ProfilaxisService, ReporteService)
from ..domain.common import utcnow
from ..domain.events import ResultadoLaboratorioAdjuntadoEvent
from ..infrastructure.config import Settings
from ..infrastructure.db import create_schema, make_engine, make_session_factory
from ..infrastructure.event_bus import InMemoryEventBus
from ..infrastructure.notifier import LogNotificador
from ..infrastructure.seed import sembrar_jaulas, sembrar_paquete_datos
from ..infrastructure.uow import SqlAlchemyUnitOfWork


@dataclass
class Container:
    bus: InMemoryEventBus
    notificador: LogNotificador
    pacientes: PacienteService
    consultas: ConsultaService
    profilaxis: ProfilaxisService
    hospitalizacion: HospitalizacionService
    ordenes: OrdenService
    reportes: ReporteService
    agenda: AgendaService
    uow_factory: Callable[[], Any]
    engine: Any = None


def build_container(settings: Settings, clock: Callable = utcnow) -> Container:
    engine = make_engine(settings.database_url)
    create_schema(engine)
    sf = make_session_factory(engine)
    bus, notif = InMemoryEventBus(), LogNotificador()
    uow_factory = lambda: SqlAlchemyUnitOfWork(sf, bus)  # noqa: E731
    sembrar_jaulas(uow_factory)  # catálogo físico de la clínica (12 perro, 6 gato, 2 aislamiento)
    if settings.seed_on_start:
        sembrar_paquete_datos(uow_factory, settings.data_dir)
    def alertar_medico(e: ResultadoLaboratorioAdjuntadoEvent) -> None:  # US14: «alerta al médico tratante»
        notif.enviar("SISTEMA", f"CED-{e.cedula_medico or 'GUARDIA'}",
                     f"Resultado de {e.tipo_estudio} recibido (consulta {e.consulta_id})")

    bus.subscribe(ResultadoLaboratorioAdjuntadoEvent, alertar_medico)
    return Container(
        bus=bus, notificador=notif, uow_factory=uow_factory, engine=engine,
        pacientes=PacienteService(uow_factory, bus, clock), consultas=ConsultaService(uow_factory, bus, clock),
        profilaxis=ProfilaxisService(uow_factory, bus, notif, clock),
        hospitalizacion=HospitalizacionService(uow_factory, bus, clock),
        ordenes=OrdenService(uow_factory, bus, clock), reportes=ReporteService(uow_factory, bus, clock),
        agenda=AgendaService(uow_factory, bus, clock))
