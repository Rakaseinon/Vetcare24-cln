"""RN-06 validación cruzada, bitácora 2–4 h y asignación de jaulas."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.domain.common import BusinessRuleViolation, InvalidStateTransition, ValidationDomainError
from src.domain.hospitalizacion import (ConstantesVitales, Criticidad, EstadoHospitalizacion as EH, Hospitalizacion,
                                        Jaula, TipoJaula)
from src.domain.paciente import Paciente
from src.domain.servicios import ServicioAltaHospitalaria, ServicioIngresoHospitalario

pytestmark = pytest.mark.unit
T0 = datetime(2026, 11, 6, 8, tzinfo=timezone.utc)
CED = "1234567"
NORMAL = ConstantesVitales("38.5", 100, 24)


def hosp(critico=False):
    return Hospitalizacion.ingresar("H1", "P1", "JP-01", "suero 20 ml/h", T0, critico)


def pac(especie="PERRO"):
    return Paciente.registrar("P1", "Rex", especie, "T1", "EXP-1", date(2026, 11, 6), peso_kg="10")


# ---------------- RN-06
def test_alta_requiere_ambas_confirmaciones_sin_importar_orden():
    for primero in ("firma", "pago"):
        h, j = hosp(), Jaula("JP-01", TipoJaula.PERRO, "H1")
        svc = ServicioAltaHospitalaria()
        a, b = (("FIRMAR_ALTA", CED), ("LIQUIDAR_CUENTA", None)) if primero == "firma" else (("LIQUIDAR_CUENTA", None), ("FIRMAR_ALTA", CED))
        assert svc.procesar(h, j, a[0], T0, a[1]) == "PENDIENTE_VALIDACION_CRUZADA"
        assert not j.libre and h.estado is EH.PENDIENTE_VALIDACION_CRUZADA and not h.es_apto_para_egreso()
        assert svc.procesar(h, j, b[0], T0, b[1]) == "EGRESO_CONCLUIDO"
        assert j.libre and h.estado is EH.EGRESADO and h.egreso_en == T0


def test_eventos_de_alta_y_liberacion():
    h, j = hosp(), Jaula("JP-01", TipoJaula.PERRO, "H1")
    s = ServicioAltaHospitalaria()
    s.procesar(h, j, "FIRMAR_ALTA", T0, CED)
    s.procesar(h, j, "LIQUIDAR_CUENTA", T0)
    assert {"AltaMedicaAutorizadaEvent", "CuentaLiquidadaEvent"} <= {e.name for e in h.pull_events()}
    assert [e.name for e in j.pull_events()] == ["JaulaLiberadaEvent"]


def test_no_permite_repetir_firma_ni_liquidacion_ni_actuar_tras_egreso():
    h, j = hosp(), Jaula("JP-01", TipoJaula.PERRO, "H1")
    h.firmar_alta_medica(CED)
    with pytest.raises(BusinessRuleViolation):
        h.firmar_alta_medica(CED)
    h.liquidar_cuenta()
    with pytest.raises(BusinessRuleViolation):
        h.liquidar_cuenta()
    assert h.intentar_egreso(T0) and not h.intentar_egreso(T0)
    for f in (lambda: h.firmar_alta_medica(CED), h.liquidar_cuenta, lambda: h.registrar_constantes(NORMAL, "enf"),
              lambda: h.agregar_consumo("x", 1)):
        with pytest.raises(BusinessRuleViolation):
            f()


def test_egresar_directo_desde_hospitalizado_es_imposible_y_accion_desconocida():
    h, j = hosp(), Jaula("JP-01", TipoJaula.PERRO, "H1")
    assert not h.intentar_egreso()
    with pytest.raises(BusinessRuleViolation):
        ServicioAltaHospitalaria().procesar(h, j, "OTRA", T0)
    with pytest.raises(ValidationDomainError):
        h.firmar_alta_medica("abc")


# ---------------- bitácora
def test_ventana_4h_estable_y_2h_critico():
    h = hosp()
    assert not h.lectura_vencida(T0 + timedelta(hours=4)) and h.lectura_vencida(T0 + timedelta(hours=4, minutes=1))
    c = hosp(critico=True)
    assert not c.lectura_vencida(T0 + timedelta(hours=2)) and c.lectura_vencida(T0 + timedelta(hours=2, minutes=1))


def test_lectura_reinicia_ventana_y_registra_autor():
    h = hosp()
    h.registrar_constantes(NORMAL, "enf1", T0 + timedelta(hours=3))
    assert not h.lectura_vencida(T0 + timedelta(hours=6)) and h.lectura_vencida(T0 + timedelta(hours=7, minutes=1))
    assert h.bitacora[0].registrada_por == "enf1"
    with pytest.raises(ValidationDomainError):
        h.registrar_constantes(NORMAL, " ")


def test_lectura_anormal_eleva_a_critico_y_emite_evento_luego_normaliza():
    h = hosp()
    alertas = h.registrar_constantes(ConstantesVitales("41", 220, 60), "enf", T0)
    assert len(alertas) == 3 and h.criticidad is Criticidad.CRITICO
    assert "SignosVitalesFueraDeRangoEvent" in [e.name for e in h.pull_events()]
    assert h.registrar_constantes(NORMAL, "enf", T0 + timedelta(hours=1)) == [] and h.criticidad is Criticidad.ESTABLE
    with pytest.raises(ValidationDomainError):
        ConstantesVitales("38", 0, 20)


def test_precuenta_suma_consumos():
    h = hosp()
    h.agregar_consumo("suero", "120.50")
    h.agregar_consumo("antibiótico", 300)
    assert h.precuenta_total == Decimal("420.50")
    with pytest.raises(ValidationDomainError):
        h.agregar_consumo("x", 0)


# ---------------- jaulas
def test_ingreso_asigna_jaula_compatible():
    s = ServicioIngresoHospitalario()
    j = Jaula("JP-01", TipoJaula.PERRO)
    h = s.ingresar(pac("PERRO"), j, "plan", False, T0)
    assert not j.libre and j.hospitalizacion_id == h.id
    with pytest.raises(BusinessRuleViolation, match="desocupada"):
        s.ingresar(pac("PERRO"), j, "plan", False, T0)


@pytest.mark.parametrize("especie,tipo,contagioso", [
    ("GATO", TipoJaula.PERRO, False), ("PERRO", TipoJaula.AISLAMIENTO, False), ("PERRO", TipoJaula.PERRO, True)])
def test_ingreso_rechaza_jaula_incompatible(especie, tipo, contagioso):
    with pytest.raises(BusinessRuleViolation):
        ServicioIngresoHospitalario().ingresar(pac(especie), Jaula("J", tipo), "plan", contagioso, T0)


def test_contagioso_va_a_aislamiento_y_jaula_no_se_ocupa_dos_veces():
    j = Jaula("JA-01", TipoJaula.AISLAMIENTO)
    ServicioIngresoHospitalario().ingresar(pac("GATO"), j, "plan", True, T0)
    with pytest.raises(BusinessRuleViolation):
        j.ocupar("otra")
