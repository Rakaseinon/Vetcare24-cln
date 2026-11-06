"""OrdenServicio: solicitud de servicios de un tutor (cita/cuenta de servicios, US02).

Es el agregado sobre el que se ejecuta el paquete de pruebas `04_VetCare_24` (ver docs/DIFERENCIAS_PAQUETE_DATOS.md).

Máquina de estados:
  SOLICITADA --aprobar--> CONFIRMADA --completar--> REALIZADA
  SOLICITADA --cancelar--> CANCELADA ;  CONFIRMADA --cancelar--> CANCELADA
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum

from .common import AggregateRoot, BusinessRuleViolation, StateMachine, ValidationDomainError
from .events import OrdenCanceladaEvent, OrdenConfirmadaEvent, OrdenRealizadaEvent
from .specifications import ContextoOrden, elegible_beneficio_referencia, puede_procesarse
from .tutor import Tutor


class EstadoOrden(str, Enum):
    SOLICITADA = "SOLICITADA"
    CONFIRMADA = "CONFIRMADA"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"


MAQUINA_ORDEN: StateMachine[EstadoOrden] = StateMachine("OrdenServicio", [
    (EstadoOrden.SOLICITADA, "aprobar", EstadoOrden.CONFIRMADA),
    (EstadoOrden.CONFIRMADA, "completar", EstadoOrden.REALIZADA),
    (EstadoOrden.SOLICITADA, "cancelar", EstadoOrden.CANCELADA),
    (EstadoOrden.CONFIRMADA, "cancelar", EstadoOrden.CANCELADA),
])


@dataclass
class ServicioCatalogo(AggregateRoot):
    id: str
    descripcion: str
    precio: Decimal
    capacidad: int
    habilitado: bool = True


@dataclass(frozen=True)
class LineaOrden:
    servicio_id: str
    descripcion: str
    precio: Decimal  # precio congelado al solicitar
    cantidad: int

    @property
    def subtotal(self) -> Decimal:
        return self.precio * self.cantidad


@dataclass
class OrdenServicio(AggregateRoot):
    id: str
    tutor_id: str
    fecha_solicitud: date
    estado: EstadoOrden = EstadoOrden.SOLICITADA
    promocion_activa: bool = False
    autorizado: bool = True
    referencia: str | None = None
    lineas: list[LineaOrden] = field(default_factory=list)

    @classmethod
    def solicitar(cls, id: str, tutor: Tutor, pedidos: list[tuple[ServicioCatalogo, int]], hoy: date,
                  promocion_activa: bool = False, autorizado: bool = True,
                  referencia: str | None = None) -> "OrdenServicio":
        """Valida cantidades, disponibilidad/capacidad e importes al crear la orden."""
        if not pedidos:
            raise ValidationDomainError("La orden debe incluir al menos un servicio")
        lineas: list[LineaOrden] = []
        for servicio, cantidad in pedidos:
            if cantidad <= 0:
                raise ValidationDomainError(f"Cantidad inválida para {servicio.id}: debe ser > 0")
            if not servicio.habilitado:
                raise BusinessRuleViolation(f"El servicio {servicio.id} no está habilitado")
            if cantidad > servicio.capacidad:
                raise BusinessRuleViolation(
                    f"Capacidad insuficiente en {servicio.id}: solicitado {cantidad}, disponible {servicio.capacidad}")
            lineas.append(LineaOrden(servicio.id, servicio.descripcion, servicio.precio, cantidad))
        return cls(id=id, tutor_id=tutor.id, fecha_solicitud=hoy, promocion_activa=promocion_activa,
                   autorizado=autorizado, referencia=referencia, lineas=lineas)

    def total(self) -> Decimal:
        return sum((l.subtotal for l in self.lineas), Decimal("0")).quantize(Decimal("0.01"))

    # ---- Specifications
    def puede_procesarse(self, tutor: Tutor) -> bool:
        return puede_procesarse().is_satisfied_by(ContextoOrden(self, tutor))

    def motivos_no_procesable(self, tutor: Tutor) -> list[str]:
        return puede_procesarse().reasons(ContextoOrden(self, tutor))

    def elegible_beneficio_referencia(self, tutor: Tutor) -> bool:
        return elegible_beneficio_referencia().is_satisfied_by(ContextoOrden(self, tutor))

    # ---- transiciones
    def aprobar(self, tutor: Tutor) -> None:
        nuevo = MAQUINA_ORDEN.fire(self.estado, "aprobar")
        motivos = self.motivos_no_procesable(tutor)
        if motivos:
            raise BusinessRuleViolation("La orden no puede procesarse: " + ", ".join(motivos))
        self.estado = nuevo
        self._record(OrdenConfirmadaEvent(orden_id=self.id))

    def completar(self) -> None:
        self.estado = MAQUINA_ORDEN.fire(self.estado, "completar")
        self._record(OrdenRealizadaEvent(orden_id=self.id))

    def cancelar(self) -> None:
        self.estado = MAQUINA_ORDEN.fire(self.estado, "cancelar")
        self._record(OrdenCanceladaEvent(orden_id=self.id))
