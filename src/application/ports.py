"""Puertos (interfaces) que la capa de aplicación necesita; la infraestructura los implementa."""
from __future__ import annotations

from typing import Any, Callable, Protocol

from ..domain.common import DomainEvent


class EventBus(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def publish_all(self, events: list[DomainEvent]) -> None: ...


class Notificador(Protocol):
    def enviar(self, canal: str, destino: str, mensaje: str) -> None: ...


class UnitOfWork(Protocol):
    """Unidad de trabajo: transacción + repositorios + publicación de eventos tras el commit."""

    tutores: Any
    servicios: Any
    pacientes: Any
    consultas: Any
    hospitalizaciones: Any
    jaulas: Any
    vacunas: Any
    ordenes: Any
    citas: Any

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, *exc: Any) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


UowFactory = Callable[[], UnitOfWork]
Clock = Callable[[], Any]
