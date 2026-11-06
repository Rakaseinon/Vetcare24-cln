"""Specifications del dominio y su composición (AND / OR / NOT).

Leaf specs = reglas atómicas; las funciones fábrica (`puede_procesarse`, `apto_para_egreso`, ...)
las componen. Trazabilidad: ver docs/TRAZABILIDAD.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable

from .common import Specification

TOTAL_MINIMO_BENEFICIO = Decimal("1500")
VENTANA_RECORDATORIO_DIAS = 2  # RF-05: 48 horas antes del vencimiento


# --------------------------------------------------------------------------- Orden de servicio
@dataclass(frozen=True)
class ContextoOrden:
    orden: Any
    tutor: Any


class TutorActivoSpec(Specification[ContextoOrden]):
    nombre = "tutor_activo"

    def is_satisfied_by(self, c: ContextoOrden) -> bool:
        return bool(c.tutor.activo)


class OrdenConLineasSpec(Specification[ContextoOrden]):
    nombre = "orden_con_al_menos_una_linea"

    def is_satisfied_by(self, c: ContextoOrden) -> bool:
        return len(c.orden.lineas) > 0


class OrdenAutorizadaSpec(Specification[ContextoOrden]):
    nombre = "orden_autorizada"

    def is_satisfied_by(self, c: ContextoOrden) -> bool:
        return bool(c.orden.autorizado)


class TutorPreferenteSpec(Specification[ContextoOrden]):
    nombre = "tutor_preferente"

    def is_satisfied_by(self, c: ContextoOrden) -> bool:
        return bool(c.tutor.es_preferente)


class TotalMinimoSpec(Specification[ContextoOrden]):
    def __init__(self, minimo: Decimal = TOTAL_MINIMO_BENEFICIO) -> None:
        self.minimo = minimo
        self.nombre = f"total>={minimo}"

    def is_satisfied_by(self, c: ContextoOrden) -> bool:
        return c.orden.total() >= self.minimo


class PromocionActivaSpec(Specification[ContextoOrden]):
    nombre = "promocion_activa"

    def is_satisfied_by(self, c: ContextoOrden) -> bool:
        return bool(c.orden.promocion_activa)


def puede_procesarse() -> Specification[ContextoOrden]:
    """tutor activo AND orden con líneas AND autorizada."""
    return TutorActivoSpec() & OrdenConLineasSpec() & OrdenAutorizadaSpec()


def elegible_beneficio_referencia() -> Specification[ContextoOrden]:
    """tutor preferente AND total >= 1500 MXN AND NOT promoción activa."""
    return TutorPreferenteSpec() & TotalMinimoSpec() & ~PromocionActivaSpec()


# --------------------------------------------------------------------------- RN-04 alergias
class AlergenoCoincideSpec(Specification[str]):
    """Candidato = principio activo prescrito."""

    nombre = "principio_activo_coincide_con_alergia"

    def __init__(self, alergenos: Iterable[Any]) -> None:
        self._set = {a.principio_activo for a in alergenos}

    def is_satisfied_by(self, principio_activo: str) -> bool:
        return principio_activo.strip().lower() in self._set


# --------------------------------------------------------------------------- RN-06 alta cruzada
class AltaMedicaFirmadaSpec(Specification[Any]):
    nombre = "alta_medica_firmada"

    def is_satisfied_by(self, h: Any) -> bool:
        return bool(h.alta_medica_firmada)


class CuentaLiquidadaSpec(Specification[Any]):
    nombre = "cuenta_liquidada"

    def is_satisfied_by(self, h: Any) -> bool:
        return bool(h.cuenta_liquidada)


def apto_para_egreso() -> Specification[Any]:
    return AltaMedicaFirmadaSpec() & CuentaLiquidadaSpec()


# --------------------------------------------------------------------------- bitácora (2-4 h)
class LecturaVencidaSpec(Specification[Any]):
    """Verdadero si ya pasó la ventana máxima sin registrar constantes (4 h; 2 h si es crítico)."""

    nombre = "lectura_de_constantes_vencida"

    def __init__(self, ahora: datetime) -> None:
        self.ahora = ahora

    def is_satisfied_by(self, h: Any) -> bool:
        return self.ahora - h.ultima_referencia() > h.ventana_maxima()


# --------------------------------------------------------------------------- profilaxis
class RefuerzoPorNotificarSpec(Specification[Any]):
    """Refuerzo sin notificar cuya fecha cae dentro de las próximas 48 h (RF-05)."""

    nombre = "refuerzo_por_notificar"

    def __init__(self, hoy: date) -> None:
        self.hoy = hoy

    def is_satisfied_by(self, registro: Any) -> bool:
        p = registro.programacion
        faltan = (p.fecha_programada - self.hoy).days
        return (not p.notificado) and 0 <= faltan <= VENTANA_RECORDATORIO_DIAS
