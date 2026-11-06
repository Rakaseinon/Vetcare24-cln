"""US02 (agenda inteligente) y US14 (laboratorio) a través de la API."""
import hashlib
from datetime import timedelta

import pytest

from tests.conftest import CEDULA, ENF, RECEP, VET
from tests.integration.test_api_clinica import consulta_con_nota, mascota, tutor

pytestmark = pytest.mark.integration


def lunes(reloj, hora=9, minuto=0):
    d = reloj().date() + timedelta(days=3)  # el reloj fijo es viernes 6-nov-2026
    return f"{d.isoformat()}T{hora:02d}:{minuto:02d}:00Z"


def test_us02_cirugia_mayor_reserva_90_min_y_asigna_quirofano(client, reloj):
    pid = mascota(client, tutor(client))
    r = client.post("/citas", json={"paciente_id": pid, "tipo": "CIRUGIA", "inicio": lunes(reloj)}, headers=RECEP)
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["duracion_min"] == 90 and c["sala"].startswith("QUIR-") and c["estado"] == "PROGRAMADA"
    assert c["acciones_permitidas"] == ["atender", "cancelar"]


@pytest.mark.parametrize("tipo,minutos", [("VACUNA", 15), ("CONSULTA_GENERAL", 30), ("ESPECIALIDAD", 45)])
def test_us02_duracion_por_servicio(client, reloj, tipo, minutos):
    pid = mascota(client, tutor(client))
    r = client.post("/citas", json={"paciente_id": pid, "tipo": tipo, "inicio": lunes(reloj)}, headers=RECEP)
    assert r.status_code == 201 and r.json()["duracion_min"] == minutos and r.json()["sala"].startswith("CONS-")


def test_us02_sobrecupo_409_y_cancelar_libera(client, reloj):
    pid = mascota(client, tutor(client))
    cuerpo = {"paciente_id": pid, "tipo": "CIRUGIA", "inicio": lunes(reloj), "duracion_min": 120}
    q1 = client.post("/citas", json=cuerpo, headers=RECEP).json()
    q2 = client.post("/citas", json=cuerpo, headers=RECEP).json()
    assert {q1["sala"], q2["sala"]} == {"QUIR-01", "QUIR-02"}
    solapada = client.post("/citas", json={**cuerpo, "inicio": lunes(reloj, 10)}, headers=RECEP)
    assert solapada.status_code == 409 and "sobrecupo" in solapada.json()["mensaje"]
    assert client.post(f"/citas/{q1['id']}/cancelar", headers=RECEP).json()["estado"] == "CANCELADA"
    libre = client.post("/citas", json={**cuerpo, "inicio": lunes(reloj, 10)}, headers=RECEP)
    assert libre.status_code == 201 and libre.json()["sala"] == q1["sala"]
    assert client.post(f"/citas/{q1['id']}/cancelar", headers=RECEP).status_code == 409  # ya cancelada


def test_us02_consulta_agenda_del_dia_y_validaciones(client, reloj):
    pid = mascota(client, tutor(client))
    a = client.post("/citas", json={"paciente_id": pid, "tipo": "VACUNA", "inicio": lunes(reloj, 11)}, headers=RECEP).json()
    b = client.post("/citas", json={"paciente_id": pid, "tipo": "VACUNA", "inicio": lunes(reloj, 8)}, headers=RECEP).json()
    dia = lunes(reloj)[:10]
    assert [c["id"] for c in client.get("/citas", params={"dia": dia}, headers=RECEP).json()] == [b["id"], a["id"]]
    assert client.get("/citas", params={"dia": "2030-01-01"}, headers=RECEP).json() == []
    assert client.get(f"/citas/{a['id']}", headers=RECEP).json()["id"] == a["id"]
    assert client.get("/citas/NOEXISTE", headers=RECEP).status_code == 404
    assert client.post("/citas", json={"paciente_id": "NOEXISTE", "tipo": "VACUNA", "inicio": lunes(reloj)},
                       headers=RECEP).status_code == 404
    assert client.post("/citas", json={"paciente_id": pid, "tipo": "PELUQUERIA", "inicio": lunes(reloj)},
                       headers=RECEP).status_code == 422
    assert client.post("/citas", json={"paciente_id": pid, "tipo": "VACUNA", "inicio": "2020-01-01T09:00:00Z"},
                       headers=RECEP).status_code == 400  # en el pasado
    assert client.post("/citas", json={"paciente_id": pid, "tipo": "CONSULTA_GENERAL", "inicio": lunes(reloj),
                                       "duracion_min": 60}, headers=RECEP).status_code == 400
    assert client.post("/citas", json={"paciente_id": pid, "tipo": "VACUNA", "inicio": lunes(reloj)},
                       headers=ENF).status_code == 403


def test_us14_laboratorio_flujo_y_alerta_al_medico(client, container):
    pid = mascota(client, tutor(client))
    cid = consulta_con_nota(client, pid)
    s = client.post(f"/consultas/{cid}/laboratorio", json={"tipo_estudio": "Hemograma completo"}, headers=VET)
    assert s.status_code == 201
    estudio = s.json()["estudios"][0]
    assert estudio["estado"] == "PENDIENTE" and estudio["resultado"] is None
    huella = hashlib.sha256(b"%PDF-1.4 hemograma").hexdigest()
    r = client.post(f"/consultas/{cid}/laboratorio/{estudio['id']}/resultado",
                    json={"nombre_archivo": "hemograma_rex.pdf", "sha256": huella}, headers=VET)
    assert r.status_code == 201 and r.json()["estudios"][0]["estado"] == "RECIBIDO"
    assert r.json()["estudios"][0]["resultado"]["sha256"] == huella
    canal, destino, mensaje = container.notificador.enviados[-1]
    assert canal == "SISTEMA" and destino == f"CED-{CEDULA}" and "Hemograma completo" in mensaje


def test_us14_validaciones_y_permisos(client):
    cid = consulta_con_nota(client, mascota(client, tutor(client)))
    est = client.post(f"/consultas/{cid}/laboratorio", json={"tipo_estudio": "Hemograma"}, headers=VET).json()["estudios"][0]
    url = f"/consultas/{cid}/laboratorio/{est['id']}/resultado"
    assert client.post(url, json={"nombre_archivo": "malware.exe"}, headers=VET).status_code == 400
    assert client.post(url, json={"nombre_archivo": "ok.pdf", "sha256": "zz"}, headers=VET).status_code == 400
    assert client.post(url, json={"nombre_archivo": "ok.pdf"}, headers=RECEP).status_code == 403  # RNF-03
    assert client.post(url, json={"nombre_archivo": "ok.pdf"}, headers=VET).status_code == 201
    assert client.post(url, json={"nombre_archivo": "otro.pdf"}, headers=VET).status_code == 409
    assert client.post(f"/consultas/{cid}/laboratorio/LAB-NOEXISTE/resultado", json={"nombre_archivo": "a.pdf"},
                       headers=VET).status_code == 404
    assert client.post("/consultas/NOEXISTE/laboratorio", json={"tipo_estudio": "x"}, headers=VET).status_code == 404
    assert client.post(f"/consultas/{cid}/laboratorio", json={"tipo_estudio": " "}, headers=VET).status_code == 400


def test_us14_adjuntar_no_viola_rn01_con_nota_firmada(client):
    cid = consulta_con_nota(client, mascota(client, tutor(client)))
    client.post(f"/consultas/{cid}/nota/firmar", json={"cedula": CEDULA}, headers=VET)
    est = client.post(f"/consultas/{cid}/laboratorio", json={"tipo_estudio": "Química"}, headers=VET).json()["estudios"][0]
    r = client.post(f"/consultas/{cid}/laboratorio/{est['id']}/resultado", json={"nombre_archivo": "q.pdf"}, headers=VET)
    assert r.status_code == 201 and r.json()["nota"]["estado"] == "CONGELADA"


def test_cancelacion_tardia_y_kpi_de_citas_canceladas(client, reloj):
    from tests.conftest import DIR
    pid = mascota(client, tutor(client))
    hoy = reloj().date().isoformat()
    pronto = f"{hoy}T13:00:00Z"  # el reloj marca 12:00Z: faltan 1 h -> cancelación tardía
    lejos = lunes(reloj)
    c1 = client.post("/citas", json={"paciente_id": pid, "tipo": "VACUNA", "inicio": pronto}, headers=RECEP).json()
    c2 = client.post("/citas", json={"paciente_id": pid, "tipo": "VACUNA", "inicio": lejos}, headers=RECEP).json()
    assert client.post(f"/citas/{c1['id']}/cancelar", headers=RECEP).json()["cancelacion_tardia"] is True
    assert client.post(f"/citas/{c2['id']}/cancelar", headers=RECEP).json()["cancelacion_tardia"] is False
    rep = client.get("/reportes/operativo", params={"desde": hoy, "hasta": lejos[:10]}, headers=DIR).json()
    assert rep["citas_canceladas"] == 2 and rep["citas_canceladas_tardias"] == 1
