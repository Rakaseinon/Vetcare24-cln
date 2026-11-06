import pytest

from src.domain.common import InvalidStateTransition
from src.domain.hospitalizacion import MAQUINA_HOSPITALIZACION, EstadoHospitalizacion as H
from src.domain.orden_servicio import MAQUINA_ORDEN, EstadoOrden as E

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("origen,accion,destino", [
    (E.SOLICITADA, "aprobar", E.CONFIRMADA), (E.CONFIRMADA, "completar", E.REALIZADA),
    (E.SOLICITADA, "cancelar", E.CANCELADA), (E.CONFIRMADA, "cancelar", E.CANCELADA)])
def test_transiciones_validas_orden(origen, accion, destino):
    assert MAQUINA_ORDEN.fire(origen, accion) is destino


@pytest.mark.parametrize("origen,accion", [
    (E.SOLICITADA, "completar"), (E.CONFIRMADA, "aprobar"), (E.REALIZADA, "cancelar"),
    (E.CANCELADA, "aprobar"), (E.REALIZADA, "completar"), (E.SOLICITADA, "inexistente")])
def test_transiciones_invalidas_orden(origen, accion):
    with pytest.raises(InvalidStateTransition):
        MAQUINA_ORDEN.fire(origen, accion)


def test_acciones_permitidas_y_tabla():
    assert MAQUINA_ORDEN.permitidas(E.SOLICITADA) == ["aprobar", "cancelar"]
    assert MAQUINA_ORDEN.permitidas(E.REALIZADA) == []
    assert ("SOLICITADA", "aprobar", "CONFIRMADA") in MAQUINA_ORDEN.tabla()


def test_maquina_hospitalizacion_no_egresa_sin_pasar_por_pendiente():
    with pytest.raises(InvalidStateTransition):
        MAQUINA_HOSPITALIZACION.fire(H.HOSPITALIZADO, "EGRESAR")
    assert MAQUINA_HOSPITALIZACION.fire(H.PENDIENTE_VALIDACION_CRUZADA, "EGRESAR") is H.EGRESADO
