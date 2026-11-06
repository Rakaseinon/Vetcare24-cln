"""Oráculo INDEPENDIENTE del paquete VetCare 24.

Recalcula el resultado esperado de los 120 casos y las 20 transiciones directamente de las columnas de los CSV
(csv + Decimal, sin importar nada de `src.domain`) y lo compara con lo que responde la API real. Así el código
no se valida contra sí mismo. Reglas: LEEME.txt del paquete (modelo de pruebas) + BRD del equipo.
"""
import csv
from decimal import Decimal

import pytest

from tests.conftest import DATA_DIR, RECEP

pytestmark = pytest.mark.integration


def leer(nombre):
    with (DATA_DIR / nombre).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


ACTORES = {r["actor_id"]: r for r in leer("actores.csv")}
CATALOGO = {r["recurso_id"]: r for r in leer("catalogo.csv")}
OPERACIONES = {r["operacion_id"]: r for r in leer("operaciones.csv")}
DETALLE: dict[str, list[dict]] = {}
for _r in leer("detalle_operaciones.csv"):
    DETALLE.setdefault(_r["operacion_id"], []).append(_r)


def total(op_id) -> Decimal:
    return sum((Decimal(CATALOGO[l["recurso_id"]]["precio_mxn"]) * int(l["cantidad"]) for l in DETALLE.get(op_id, [])),
               Decimal("0"))


def esperado_valida(op_id) -> bool:
    op = OPERACIONES[op_id]
    return ACTORES[op["actor_id"]]["activo"] == "1" and len(DETALLE.get(op_id, [])) > 0 and op["autorizado"] == "1"


def esperado_beneficio(op_id) -> bool:
    op = OPERACIONES[op_id]
    return ACTORES[op["actor_id"]]["es_preferente"] == "1" and total(op_id) >= Decimal("1500") and op["promocion_activa"] == "0"


CASOS = leer("casos_prueba.csv")
TRANSICIONES = leer("transiciones_prueba.csv")


def test_el_paquete_trae_lo_prometido():
    assert (len(ACTORES), len(CATALOGO), len(OPERACIONES), len(CASOS), len(TRANSICIONES)) == (40, 20, 60, 120, 20)


@pytest.mark.parametrize("caso", CASOS, ids=[c["caso_id"] for c in CASOS])
def test_casos_de_prueba_contra_oraculo(client, caso):
    op = client.get(f"/ordenes/{caso['operacion_id']}", headers=RECEP)
    assert op.status_code == 200
    cuerpo = op.json()
    assert Decimal(cuerpo["total"]) == total(caso["operacion_id"])
    if caso["tipo_prueba"] == "validar_operacion":
        assert cuerpo["puede_procesarse"] is esperado_valida(caso["operacion_id"])
        assert (cuerpo["motivos_no_procesable"] == []) is cuerpo["puede_procesarse"]
    else:
        assert caso["tipo_prueba"] == "evaluar_beneficio"
        assert cuerpo["elegible_beneficio_referencia"] is esperado_beneficio(caso["operacion_id"])


def esperado_transicion(accion, op_id):
    """(codigo HTTP, estado final) esperado, derivado del flujo de referencia SOLICITADA→CONFIRMADA→REALIZADA / CANCELADA."""
    valida = esperado_valida(op_id)
    if accion == "aprobar":
        return (200, "CONFIRMADA") if valida else (409, "SOLICITADA")
    if accion == "cancelar":
        return 200, "CANCELADA"
    if accion == "completar" or accion == "saltar_estado":
        return 409, "SOLICITADA"  # no se puede completar sin confirmar
    if accion == "repetir_aprobacion":
        return (409, "CONFIRMADA") if valida else (409, "SOLICITADA")  # la 1.ª o la 2.ª aprobación falla
    raise AssertionError(accion)


@pytest.mark.parametrize("tr", TRANSICIONES, ids=[t["caso_id"] for t in TRANSICIONES])
def test_transiciones_contra_oraculo(client, tr):
    oid, accion = tr["operacion_id"], tr["accion_sugerida"]
    codigo, final = esperado_transicion(accion, oid)
    if accion == "saltar_estado":
        r = client.post(f"/ordenes/{oid}/transiciones", json={"accion": "completar"}, headers=RECEP)
    elif accion == "repetir_aprobacion":
        client.post(f"/ordenes/{oid}/transiciones", json={"accion": "aprobar"}, headers=RECEP)
        r = client.post(f"/ordenes/{oid}/transiciones", json={"accion": "aprobar"}, headers=RECEP)
    else:
        r = client.post(f"/ordenes/{oid}/transiciones", json={"accion": accion}, headers=RECEP)
    assert r.status_code == codigo, r.text
    assert client.get(f"/ordenes/{oid}", headers=RECEP).json()["estado"] == final
    if codigo == 409:
        assert r.json()["codigo"] in {"InvalidStateTransition", "BusinessRuleViolation"}


def test_resumen_del_paquete_coincide_con_runner(tmp_path):
    """El runner de scripts/ produce los mismos veredictos que el oráculo."""
    from scripts.ejecutar_casos_prueba import ejecutar, leer as leer_res

    ejecutar(DATA_DIR, tmp_path)
    _, filas = leer_res(tmp_path / "casos_prueba_resultado.csv")
    assert len(filas) == 120 and all(f["resultado_alumno"] != "PENDIENTE" for f in filas)
    for f in filas:
        if f["tipo_prueba"] == "validar_operacion":
            assert f["resultado_alumno"].startswith("VALIDA") is esperado_valida(f["operacion_id"])
        else:
            assert (f["resultado_alumno"] == "APLICA") is esperado_beneficio(f["operacion_id"])
