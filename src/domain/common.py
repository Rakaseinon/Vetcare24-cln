"""Bloques base del dominio: errores, eventos, agregado raíz, Specification y State Machine.

Sin dependencias de infraestructura (ADR-001: desacoplamiento y testabilidad).
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, Iterable, TypeVar

T = TypeVar("T")
S = TypeVar("S", bound=Enum)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------- errores
class DomainError(Exception):
    """Base de errores de dominio."""


class ValidationDomainError(DomainError):
    """Dato inválido (HTTP 400)."""


class BusinessRuleViolation(DomainError):
    """Regla de negocio o estado incompatible (HTTP 409)."""


class InvalidStateTransition(BusinessRuleViolation):
    """Transición no permitida por la máquina de estados (HTTP 409)."""


class NotaInmutableError(BusinessRuleViolation):
    """RN-01: intento de modificar una nota/receta firmada."""


class AlergiaBloqueoError(BusinessRuleViolation):
    """RN-04: el principio activo coincide con una alergia registrada."""

    def __init__(self, message: str, event: "DomainEvent") -> None:
        super().__init__(message)
        self.event = event


class EntityNotFound(DomainError):
    """Entidad inexistente (HTTP 404)."""


# --------------------------------------------------------------------------- eventos
@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=utcnow)

    @property
    def name(self) -> str:
        return type(self).__name__


class AggregateRoot:
    """Acumula eventos de dominio hasta que el UnitOfWork los publica tras el commit."""

    def _record(self, event: DomainEvent) -> None:
        self.__dict__.setdefault("_events", []).append(event)

    def pull_events(self) -> list[DomainEvent]:
        return self.__dict__.pop("_events", [])


# --------------------------------------------------------------------------- Specification
class Specification(ABC, Generic[T]):
    """Patrón Specification (Evans/Fowler) con composición AND / OR / NOT."""

    nombre: str = ""

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool: ...

    def reasons(self, candidate: T) -> list[str]:
        """Nombres de las especificaciones hoja que impiden el cumplimiento."""
        return [] if self.is_satisfied_by(candidate) else [self.nombre or type(self).__name__]

    def and_(self, other: "Specification[T]") -> "Specification[T]":
        return AndSpecification(self, other)

    def or_(self, other: "Specification[T]") -> "Specification[T]":
        return OrSpecification(self, other)

    def not_(self) -> "Specification[T]":
        return NotSpecification(self)

    __and__ = and_
    __or__ = or_
    __invert__ = not_


class AndSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self.left, self.right = left, right
        self.nombre = f"({left.nombre} AND {right.nombre})"

    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) and self.right.is_satisfied_by(candidate)

    def reasons(self, candidate: T) -> list[str]:
        return self.left.reasons(candidate) + self.right.reasons(candidate)


class OrSpecification(Specification[T]):
    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self.left, self.right = left, right
        self.nombre = f"({left.nombre} OR {right.nombre})"

    def is_satisfied_by(self, candidate: T) -> bool:
        return self.left.is_satisfied_by(candidate) or self.right.is_satisfied_by(candidate)

    def reasons(self, candidate: T) -> list[str]:
        if self.is_satisfied_by(candidate):
            return []
        return self.left.reasons(candidate) + self.right.reasons(candidate)


class NotSpecification(Specification[T]):
    def __init__(self, inner: Specification[T]) -> None:
        self.inner = inner
        self.nombre = f"NOT {inner.nombre}"

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self.inner.is_satisfied_by(candidate)

    def reasons(self, candidate: T) -> list[str]:
        return [] if self.is_satisfied_by(candidate) else [self.nombre]


# --------------------------------------------------------------------------- State Machine
class StateMachine(Generic[S]):
    """Máquina de estados explícita: tabla (estado, acción) -> estado."""

    def __init__(self, nombre: str, transiciones: Iterable[tuple[S, str, S]]) -> None:
        self.nombre = nombre
        self._tabla: dict[tuple[S, str], S] = {(o, a): d for o, a, d in transiciones}

    def fire(self, estado: S, accion: str) -> S:
        try:
            return self._tabla[(estado, accion)]
        except KeyError:
            raise InvalidStateTransition(
                f"{self.nombre}: la acción '{accion}' no está permitida en el estado {estado.value}"
            ) from None

    def permitidas(self, estado: S) -> list[str]:
        return sorted(a for (o, a) in self._tabla if o == estado)

    def tabla(self) -> list[tuple[str, str, str]]:
        return [(o.value, a, d.value) for (o, a), d in self._tabla.items()]


def require_text(valor: Any, campo: str) -> str:
    if valor is None or not str(valor).strip():
        raise ValidationDomainError(f"'{campo}' es obligatorio")
    return str(valor).strip()
