"""Flujos clínicos de extremo a extremo a través de la API REST (US01…US15, RN-01…RN-06, RNF-03)."""
from datetime import date, timedelta

import pytest

from tests.conftest import CEDULA, DIR, ENF, RECEP, VET

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------- helpers
def tutor(client, nombre="Ana López", **kw):
    r = client.post("/tutores", json={"nombre": nombre, "identificacion_oficial": "INE-1", "telefono": "8111", **kw},
                    headers=RECEP)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def mascota(client, tutor_id, especie="PERRO", **kw):
    body = {"tutor_id": tutor_id, "nombre": "Rex", "especie": especie, "peso_kg": "10", "fecha_nacimiento": "2025-01-10", **kw}
    r = client.post("/pacientes", json=body, headers=RECEP)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def consulta_con_nota(client, pid):
    cid = client.post("/consultas", json={"paciente_id": pid, "cedula_veterinario": CEDULA}, headers=VET).json()["id"]
    r = client.put(f"/consultas/{cid}/nota", json={"subjetivo": "s", "objetivo": "o", "analisis": "a", "plan": "p"}, headers=VET)
    assert r.status_code == 200, r.text
    return cid


RECETA = {"principio_activo": "penicilina", "dosis_mg_por_kg": "10", "via": "oral", "frecuencia_horas": 12, "duracion_dias": 5}


# ---------------------------------------------------------------- salud, contrato y RBAC
def test_health_y_openapi(client):
    assert client.get("/health").json() == {"status": "ok", "environment": "test"}
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "VetCare 24 API" and len(spec["paths"]) >= 30
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize("headers,codigo", [({}, 401), ({"X-Rol": "HACKER"}, 401), ({"X-Rol": "ENFERMERIA"}, 403)])
def test_rbac_rechaza(client, headers, codigo):
    assert client.get("/servicios", headers=headers).status_code == codigo


def test_rbac_enfermeria_no_firma_ni_receta_pero_si_registra_constantes(client):
    pid = mascota(client, tutor(client))
    cid = consulta_con_nota(client, pid)
    assert client.post(f"/consultas/{cid}/nota/firmar", json={"cedula": CEDULA}, headers=ENF).status_code == 403
    assert client.post(f"/consultas/{cid}/recetas", json=RECETA, headers=ENF).status_code == 403


def test_codigos_400_404_422(client):
    assert client.get("/pacientes/NOEXISTE", headers=RECEP).status_code == 404
    assert client.get("/ordenes/NOEXISTE", headers=RECEP).status_code == 404
    assert client.post("/tutores", json={"nombre": "A", "identificacion_oficial": "I"}, headers=RECEP).status_code == 400
    assert client.post("/tutores", json={"nombre": "A"}, headers=RECEP).status_code == 422
    assert client.post("/pacientes", json={"tutor_id": "NOEXISTE", "nombre": "x", "especie": "PERRO"},
                       headers=RECEP).status_code == 404


# ---------------------------------------------------------------- US01 / US12 / RN-05 identidad
def test_us01_registro_y_busqueda_por_microchip_y_nombre(client):
    t = tutor(client, "María Pérez")
    pid = mascota(client, t, microchip="985112003456789")
    assert client.get("/pacientes/buscar", params={"q": "985112003456789"}, headers=RECEP).json()[0]["id"] == pid
    assert client.get("/pacientes/buscar", params={"q": "rex"}, headers=RECEP).json()[0]["id"] == pid
    assert client.get("/pacientes/buscar", params={"q": "8111"}, headers=RECEP).json()[0]["id"] == pid  # RF-01: teléfono del dueño
    assert client.get("/pacientes/buscar", params={"q": "EXP-000001"}, headers=RECEP).json() != []
    assert client.get("/pacientes/buscar", params={"q": "x"}, headers=RECEP).status_code == 422
    dup = client.post("/pacientes", json={"tutor_id": t, "nombre": "Otro", "especie": "PERRO", "microchip": "985112003456789"},
                      headers=RECEP)
    assert dup.status_code == 409


def test_rn05_transferencia_de_tutor_conserva_historial(client):
    t1, t2 = tutor(client, "Uno"), tutor(client, "Dos")
    pid = mascota(client, t1)
    client.post(f"/pacientes/{pid}/alergias", json={"principio_activo": "penicilina"}, headers=VET)
    r = client.post(f"/pacientes/{pid}/transferencia", json={"nuevo_tutor_id": t2}, headers=RECEP)
    assert r.status_code == 200 and r.json()["tutor_id"] == t2 and r.json()["alergias"] == ["penicilina"]
    exp = client.get(f"/pacientes/{pid}/expediente", headers=VET).json()
    assert len(exp["paciente"]["titularidad"]) == 2 and exp["paciente"]["alergias"] == ["penicilina"]
    assert client.post(f"/pacientes/{pid}/transferencia", json={"nuevo_tutor_id": t2}, headers=RECEP).status_code == 409
    assert client.post(f"/pacientes/{pid}/transferencia", json={"nuevo_tutor_id": "NOEXISTE"}, headers=RECEP).status_code == 404


# ---------------------------------------------------------------- US05 / US13 / RN-01 nota inmutable y enmiendas
def test_rn01_nota_firmada_es_inmutable_y_admite_enmiendas(client):
    cid = consulta_con_nota(client, mascota(client, tutor(client)))
    assert client.post(f"/consultas/{cid}/nota/firmar", json={"cedula": CEDULA}, headers=VET).status_code == 200
    r = client.put(f"/consultas/{cid}/nota", json={"subjetivo": "X", "objetivo": "X", "analisis": "X", "plan": "X"}, headers=VET)
    assert r.status_code == 409 and r.json()["codigo"] == "NotaInmutableError"
    assert client.post(f"/consultas/{cid}/nota/firmar", json={"cedula": CEDULA}, headers=VET).status_code == 409
    e = client.post(f"/consultas/{cid}/enmiendas", json={"cedula": "7654321", "motivo": "dosis", "detalle": "corregir"}, headers=VET)
    assert e.status_code == 201
    c = client.get(f"/consultas/{cid}", headers=VET).json()
    assert c["nota"]["subjetivo"] == "s" and len(c["enmiendas"]) == 1


def test_enmienda_sobre_nota_sin_firmar_es_409(client):
    cid = consulta_con_nota(client, mascota(client, tutor(client)))
    assert client.post(f"/consultas/{cid}/enmiendas", json={"cedula": CEDULA, "motivo": "m", "detalle": "d"},
                       headers=VET).status_code == 409


# ---------------------------------------------------------------- US06 / RN-04 alergia
def test_rn04_bloqueo_justificacion_y_sin_alergia(client):
    pid = mascota(client, tutor(client))
    cid = consulta_con_nota(client, pid)
    assert client.post(f"/consultas/{cid}/recetas", json=RECETA, headers=VET).status_code == 201  # aún sin alergia
    client.post(f"/pacientes/{pid}/alergias", json={"principio_activo": "Penicilina"}, headers=VET)
    eventos = []
    from src.domain.events import BloqueoAlergiaDisparadoEvent
    client.app.state.container.bus.subscribe(BloqueoAlergiaDisparadoEvent, eventos.append)
    bloq = client.post(f"/consultas/{cid}/recetas", json=RECETA, headers=VET)
    assert bloq.status_code == 409 and bloq.json()["codigo"] == "AlergiaBloqueoError"
    assert len(eventos) == 1  # el bloqueo queda auditado aunque la transacción se revierta
    assert len(client.get(f"/consultas/{cid}", headers=VET).json()["receta"]) == 1
    ok = client.post(f"/consultas/{cid}/recetas", json={**RECETA, "justificacion": "riesgo/beneficio", "cedula_justificante": CEDULA},
                     headers=VET)
    assert ok.status_code == 201 and len(ok.json()["receta"]) == 2
    otro = client.post(f"/consultas/{cid}/recetas", json={**RECETA, "principio_activo": "meloxicam"}, headers=VET)
    assert otro.status_code == 201


# ---------------------------------------------------------------- US03 / US04 / RN-02 urgencias y triaje
def test_rn02_urgencia_sin_datos_administrativos_y_regularizacion(client):
    r = client.post("/urgencias", json={"descripcion_trauma": "atropellamiento"}, headers=RECEP)
    assert r.status_code == 201 and r.json()["triage"] == "ROJO" and r.json()["paciente_id"] is None
    pid = mascota(client, tutor(client))
    reg = client.post(f"/urgencias/{r.json()['id']}/regularizar", params={"paciente_id": pid}, headers=RECEP)
    assert reg.status_code == 200 and reg.json()["paciente_id"] == pid


def test_us04_triaje_actualiza_peso_y_alergias(client):
    pid = mascota(client, tutor(client))
    r = client.post(f"/pacientes/{pid}/triaje", json={"peso_kg": "11.5", "temperatura_c": "39.1", "motivo": "vómito",
                                                      "alergias": ["penicilina"], "nivel": "AMARILLO"}, headers=ENF)
    assert r.status_code == 200 and r.json()["alerta_alergia"] and r.json()["peso_kg"] == "11.5"
    assert client.post(f"/pacientes/{pid}/triaje", json={"peso_kg": "11", "temperatura_c": "99", "motivo": "x"},
                       headers=ENF).status_code == 400


# ---------------------------------------------------------------- US07 / US08 / RN-03 profilaxis
def test_rn03_vacuna_exige_lote_y_marca_y_calcula_refuerzo(client, reloj):
    hoy = reloj().date()  # el reloj de prueba está fijo: no depender del día real
    pid = mascota(client, tutor(client))
    base = {"paciente_id": pid, "nombre_vacuna": "Quíntuple", "fecha_aplicacion": hoy.isoformat()}
    assert client.post("/vacunas", json=base, headers=VET).status_code == 400
    assert client.post("/vacunas", json={**base, "lote": "L1"}, headers=VET).status_code == 400
    ok = client.post("/vacunas", json={**base, "lote": "L1", "marca": "Zoetis", "esquema": "CACHORRO_28"}, headers=VET)
    assert ok.status_code == 201 and ok.json()["intervalo_dias"] == 28
    assert date.fromisoformat(ok.json()["fecha_refuerzo"]) == hoy + timedelta(days=28)


def test_us08_recordatorio_48h_antes_se_envia_una_sola_vez(client, reloj):
    pid = mascota(client, tutor(client, canal_preferido="WHATSAPP"))
    hoy = reloj().date()
    v = client.post("/vacunas", json={"paciente_id": pid, "nombre_vacuna": "Rabia", "lote": "L", "marca": "M",
                                      "fecha_aplicacion": (hoy - timedelta(days=19)).isoformat(), "esquema": "CACHORRO_21"},
                    headers=VET)
    assert v.status_code == 201 and v.json()["fecha_refuerzo"] == (hoy + timedelta(days=2)).isoformat()
    assert client.post("/recordatorios/procesar", headers=RECEP).json()["enviados"] == 1
    assert client.post("/recordatorios/procesar", headers=RECEP).json()["enviados"] == 0
    assert client.app.state.container.notificador.enviados[0][0] == "WHATSAPP"


# ---------------------------------------------------------------- US09 / US10 / US11 / RN-06 hospitalización
def hospitalizar(client, especie="PERRO", jaula=None, **kw):
    pid = mascota(client, tutor(client), especie)
    jaula = jaula or ("JG-01" if especie == "GATO" else "JP-01")
    r = client.post("/hospitalizaciones", json={"paciente_id": pid, "jaula_id": jaula, "plan_fluidoterapia": "NaCl 20 ml/h", **kw},
                    headers=VET)
    return r


def test_ingreso_y_ocupacion_de_jaulas(client):
    assert len(client.get("/jaulas", headers=ENF).json()) == 20
    r = hospitalizar(client)
    assert r.status_code == 201 and r.json()["estado"] == "HOSPITALIZADO"
    assert next(j for j in client.get("/jaulas", headers=ENF).json() if j["id"] == "JP-01")["libre"] is False
    assert hospitalizar(client).status_code == 409  # JP-01 ocupada
    assert hospitalizar(client, "GATO", "JP-02").status_code == 409  # gato en jaula de perro
    assert hospitalizar(client, jaula="NOEXISTE").status_code == 404
    assert len(client.get("/jaulas", params={"libres": True}, headers=ENF).json()) == 19


def test_us10_bitacora_alertas_y_precuenta(client, reloj):
    hid = hospitalizar(client).json()["id"]
    c = {"temperatura_c": "38.5", "frecuencia_cardiaca": 100, "frecuencia_respiratoria": 24, "registrada_por": "enf1"}
    assert client.get("/hospitalizaciones/alertas/lecturas-vencidas", headers=ENF).json() == []
    reloj.avanzar(hours=4, minutes=1)
    assert [h["id"] for h in client.get("/hospitalizaciones/alertas/lecturas-vencidas", headers=ENF).json()] == [hid]
    r = client.post(f"/hospitalizaciones/{hid}/constantes", json=c, headers=ENF)
    assert r.status_code == 201 and client.get("/hospitalizaciones/alertas/lecturas-vencidas", headers=ENF).json() == []
    crit = client.post(f"/hospitalizaciones/{hid}/constantes", json={**c, "temperatura_c": "41.5"}, headers=ENF)
    assert crit.json()["criticidad"] == "CRITICO"
    client.post(f"/hospitalizaciones/{hid}/consumos", json={"descripcion": "suero", "monto": "120.50"}, headers=ENF)
    r = client.post(f"/hospitalizaciones/{hid}/consumos", json={"descripcion": "antibiótico", "monto": "300"}, headers=ENF)
    assert r.json()["precuenta_total"] == "420.50"
    assert client.post(f"/hospitalizaciones/{hid}/consumos", json={"descripcion": "x", "monto": "-1"}, headers=ENF).status_code == 400


@pytest.mark.parametrize("orden", [("alta", "pago"), ("pago", "alta")])
def test_rn06_alta_cruzada_libera_jaula_solo_con_ambas(client, orden):
    hid = hospitalizar(client).json()["id"]

    def paso(x):
        if x == "alta":
            return client.post(f"/hospitalizaciones/{hid}/alta-medica", json={"cedula": CEDULA}, headers=VET)
        return client.post(f"/hospitalizaciones/{hid}/liquidacion", headers=RECEP)

    r1 = paso(orden[0])
    assert r1.status_code == 200 and r1.json()["resultado"] == "PENDIENTE_VALIDACION_CRUZADA"
    assert next(j for j in client.get("/jaulas", headers=ENF).json() if j["id"] == "JP-01")["libre"] is False
    assert paso(orden[0]).status_code == 409  # repetir el mismo paso
    r2 = paso(orden[1])
    assert r2.json()["resultado"] == "EGRESO_CONCLUIDO" and r2.json()["hospitalizacion"]["apto_para_egreso"]
    assert next(j for j in client.get("/jaulas", headers=ENF).json() if j["id"] == "JP-01")["libre"] is True
    assert hospitalizar(client).status_code == 201  # la jaula vuelve a estar disponible


def test_rbac_alta_solo_veterinario_y_liquidacion_solo_recepcion(client):
    hid = hospitalizar(client).json()["id"]
    assert client.post(f"/hospitalizaciones/{hid}/alta-medica", json={"cedula": CEDULA}, headers=RECEP).status_code == 403
    assert client.post(f"/hospitalizaciones/{hid}/liquidacion", headers=VET).status_code == 403


# ---------------------------------------------------------------- órdenes de servicio (paquete de datos)
def test_orden_por_api_flujo_completo_y_validaciones(client):
    t = tutor(client)
    body = {"tutor_id": t, "lineas": [{"servicio_id": "VET-P001", "cantidad": 2}, {"servicio_id": "VET-P002", "cantidad": 1}]}
    r = client.post("/ordenes", json=body, headers=RECEP)
    assert r.status_code == 201 and r.json()["total"] == "1010.00" and r.json()["estado"] == "SOLICITADA"
    oid = r.json()["id"]
    assert r.json()["acciones_permitidas"] == ["aprobar", "cancelar"]
    assert client.post(f"/ordenes/{oid}/transiciones", json={"accion": "completar"}, headers=RECEP).status_code == 409
    assert client.post(f"/ordenes/{oid}/transiciones", json={"accion": "aprobar"}, headers=RECEP).json()["estado"] == "CONFIRMADA"
    assert client.post(f"/ordenes/{oid}/transiciones", json={"accion": "completar"}, headers=RECEP).json()["estado"] == "REALIZADA"
    assert client.post(f"/ordenes/{oid}/transiciones", json={"accion": "cancelar"}, headers=RECEP).status_code == 409
    assert client.post(f"/ordenes/{oid}/transiciones", json={"accion": "volar"}, headers=RECEP).status_code == 422
    for lineas in ([], [{"servicio_id": "VET-P001", "cantidad": 0}], [{"servicio_id": "VET-P011", "cantidad": 1}],
                   [{"servicio_id": "VET-P015", "cantidad": 99}]):
        assert client.post("/ordenes", json={"tutor_id": t, "lineas": lineas}, headers=RECEP).status_code in (400, 409)
    assert client.post("/ordenes", json={"tutor_id": t, "lineas": [{"servicio_id": "NOEXISTE", "cantidad": 1}]},
                       headers=RECEP).status_code == 404
    assert len(client.get("/servicios", headers=RECEP).json()) == 20


def test_orden_no_autorizada_no_se_aprueba(client):
    r = client.post("/ordenes", json={"tutor_id": tutor(client), "autorizado": False,
                                      "lineas": [{"servicio_id": "VET-P001", "cantidad": 1}]}, headers=RECEP)
    oid = r.json()["id"]
    assert r.json()["motivos_no_procesable"] == ["orden_autorizada"]
    a = client.post(f"/ordenes/{oid}/transiciones", json={"accion": "aprobar"}, headers=RECEP)
    assert a.status_code == 409 and "orden_autorizada" in a.json()["mensaje"]


# ---------------------------------------------------------------- US15 reportes
def test_reporte_operativo_solo_director(client):
    hospitalizar(client)
    assert client.get("/reportes/operativo", headers=VET).status_code == 403
    r = client.get("/reportes/operativo", headers=DIR)
    assert r.status_code == 200 and r.json()["tasa_ocupacion"] == pytest.approx(1 / 20)


# ---------------------------------------------------------------- reglas movidas al dominio (ADR-001: Service Layer delgada)
def test_tutor_inactivo_del_dataset_no_registra_mascotas_ni_recibe_titularidad(client):
    import csv
    from tests.conftest import DATA_DIR
    with (DATA_DIR / "actores.csv").open(encoding="utf-8-sig") as f:
        inactivo = next(r["actor_id"] for r in csv.DictReader(f) if r["activo"] == "0")
    r = client.post("/pacientes", json={"tutor_id": inactivo, "nombre": "Luna", "especie": "GATO"}, headers=RECEP)
    assert r.status_code == 409 and "inactivo" in r.json()["mensaje"]
    pid = mascota(client, tutor(client))
    assert client.post(f"/pacientes/{pid}/transferencia", json={"nuevo_tutor_id": inactivo}, headers=RECEP).status_code == 409


def test_urgencia_sin_regularizar_no_puede_prescribir_ni_pedir_laboratorio(client):
    cid = client.post("/urgencias", json={"descripcion_trauma": "atropellamiento"}, headers=RECEP).json()["id"]
    assert client.post(f"/consultas/{cid}/recetas", json=RECETA, headers=VET).status_code == 409
    assert client.post(f"/consultas/{cid}/laboratorio", json={"tipo_estudio": "Hemograma"}, headers=VET).status_code == 409


def test_rnf01_expediente_clinico_abre_en_menos_de_3_segundos(client):
    """RNF-01: apertura del expediente < 3 s (medido en proceso, con un paciente con historia clínica)."""
    import time
    pid = mascota(client, tutor(client))
    for _ in range(5):
        cid = consulta_con_nota(client, pid)
        client.post(f"/consultas/{cid}/nota/firmar", json={"cedula": CEDULA}, headers=VET)
    t0 = time.perf_counter()
    r = client.get(f"/pacientes/{pid}/expediente", headers=VET)
    assert r.status_code == 200 and len(r.json()["consultas"]) == 5
    assert time.perf_counter() - t0 < 3.0


def test_rnf03_recepcion_no_accede_al_detalle_clinico(client):
    pid = mascota(client, tutor(client))
    cid = consulta_con_nota(client, pid)
    for url in (f"/pacientes/{pid}/expediente", f"/consultas/{cid}"):
        assert client.get(url, headers=RECEP).status_code == 403
        assert client.get(url, headers=VET).status_code == 200
