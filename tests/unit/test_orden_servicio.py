"""Reglas de la orden de servicio (Specifications + State Machine) — paquete VetCare 24."""
from datetime import date
from decimal import Decimal

import pytest

from src.domain.common import BusinessRuleViolation, InvalidStateTransition, ValidationDomainError
from src.domain.orden_servicio import EstadoOrden, LineaOrden, OrdenServicio, ServicioCatalogo
from src.domain.tutor import Tutor

pytestmark = pytest.mark.unit
HOY = date(2026, 11, 6)


def tutor(activo=True, pref=False):
    return Tutor(id="T1", nombre="Ana", activo=activo, es_preferente=pref)


def servicio(id="S1", precio="800", cap=10, hab=True):
    return ServicioCatalogo(id, "Consulta", Decimal(precio), cap, hab)


def orden(t=None, lineas=None, promo=False, aut=True):
    t = t or tutor()
    return OrdenServicio(id="O1", tutor_id=t.id, fecha_solicitud=HOY, promocion_activa=promo, autorizado=aut,
                         lineas=lineas if lineas is not None else [LineaOrden("S1", "Consulta", Decimal("800"), 1)])


@pytest.mark.parametrize("activo,lineas,aut,esperado", [
    (True, True, True, True), (False, True, True, False), (True, False, True, False), (True, True, False, False),
    (False, False, False, False)])
def test_puede_procesarse_tabla_de_verdad(activo, lineas, aut, esperado):
    t = tutor(activo=activo)
    o = orden(t, lineas=None if lineas else [], aut=aut)
    assert o.puede_procesarse(t) is esperado
    assert (o.motivos_no_procesable(t) == []) is esperado


def test_motivos_nombran_cada_regla_incumplida():
    t = tutor(activo=False)
    o = orden(t, lineas=[], aut=False)
    assert o.motivos_no_procesable(t) == ["tutor_activo", "orden_con_al_menos_una_linea", "orden_autorizada"]


@pytest.mark.parametrize("pref,total_precio,promo,esperado", [
    (True, "1500", False, True), (True, "1499.99", False, False), (True, "2000", True, False),
    (False, "2000", False, False), (True, "1500.00", False, True)])
def test_beneficio_referencia(pref, total_precio, promo, esperado):
    t = tutor(pref=pref)
    o = orden(t, lineas=[LineaOrden("S1", "x", Decimal(total_precio), 1)], promo=promo)
    assert o.elegible_beneficio_referencia(t) is esperado


def test_total_suma_lineas_con_cantidad():
    o = orden(lineas=[LineaOrden("S1", "a", Decimal("100.50"), 2), LineaOrden("S2", "b", Decimal("50"), 3)])
    assert o.total() == Decimal("351.00")


def test_flujo_feliz_y_eventos():
    t = tutor()
    o = orden(t)
    o.aprobar(t)
    o.completar()
    assert o.estado is EstadoOrden.REALIZADA
    assert [e.name for e in o.pull_events()] == ["OrdenConfirmadaEvent", "OrdenRealizadaEvent"]
    assert o.pull_events() == []


def test_aprobar_dos_veces_falla_por_estado():
    t = tutor()
    o = orden(t)
    o.aprobar(t)
    with pytest.raises(InvalidStateTransition):
        o.aprobar(t)


def test_aprobar_con_tutor_inactivo_no_cambia_estado():
    t = tutor(activo=False)
    o = orden(t)
    with pytest.raises(BusinessRuleViolation, match="tutor_activo"):
        o.aprobar(t)
    assert o.estado is EstadoOrden.SOLICITADA


def test_saltar_estado_y_cancelar_terminal():
    t = tutor()
    o = orden(t)
    with pytest.raises(InvalidStateTransition):
        o.completar()
    o.cancelar()
    with pytest.raises(InvalidStateTransition):
        o.aprobar(t)


def test_solicitar_valida_cantidad_capacidad_y_habilitado():
    t = tutor()
    o = OrdenServicio.solicitar("O9", t, [(servicio(), 2)], HOY)
    assert o.total() == Decimal("1600.00") and o.lineas[0].precio == Decimal("800")
    with pytest.raises(ValidationDomainError):
        OrdenServicio.solicitar("O", t, [], HOY)
    with pytest.raises(ValidationDomainError):
        OrdenServicio.solicitar("O", t, [(servicio(), 0)], HOY)
    with pytest.raises(BusinessRuleViolation, match="Capacidad"):
        OrdenServicio.solicitar("O", t, [(servicio(cap=1), 2)], HOY)
    with pytest.raises(BusinessRuleViolation, match="habilitado"):
        OrdenServicio.solicitar("O", t, [(servicio(hab=False), 1)], HOY)
