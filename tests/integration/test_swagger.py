"""El Swagger es parte de la entrega (PIA: «Swagger UI/OpenAPI activo»): debe ser claro y no desincronizarse del código."""
import pytest

from src.api import schemas as s
from src.api.docs import DOCS, TAGS
from tests.conftest import DIR

pytestmark = pytest.mark.integration

MODELOS_ENTRADA = [n for n in dir(s) if n.endswith("In") and isinstance(getattr(s, n), type)]


def test_toda_operacion_tiene_resumen_explicacion_y_roles(client):
    esquema = client.get("/openapi.json").json()
    for ruta, operaciones in esquema["paths"].items():
        for metodo, op in operaciones.items():
            assert op.get("summary"), f"{metodo} {ruta} sin resumen"
            assert "Roles con acceso" in op.get("description", ""), f"{metodo} {ruta} sin explicación/roles"
            assert op["tags"][0][0].isdigit(), f"{metodo} {ruta} fuera de un grupo numerado"


def test_el_diccionario_de_textos_coincide_con_las_rutas_reales(client):
    reales = {(m.upper(), p) for p, ops in client.get("/openapi.json").json()["paths"].items() for m in ops}
    assert set(DOCS) == reales  # ni textos huérfanos ni rutas sin documentar


def test_los_roles_documentados_salen_de_la_dependencia_real(client):
    op = client.get("/openapi.json").json()["paths"]["/reportes/operativo"]["get"]
    assert "`DIRECTOR`" in op["description"] and "RECEPCION" not in op["description"]
    assert "cualquiera" in client.get("/openapi.json").json()["paths"]["/health"]["get"]["description"]


def test_etiquetas_ordenadas_y_con_descripcion(client):
    etiquetas = client.get("/openapi.json").json()["tags"]
    assert [t["name"] for t in etiquetas] == [t["name"] for t in TAGS]
    assert all(t["description"] for t in etiquetas)


@pytest.mark.parametrize("nombre", MODELOS_ENTRADA)
def test_cada_cuerpo_de_entrada_trae_un_ejemplo_valido(nombre):
    modelo = getattr(s, nombre)
    ejemplos = modelo.model_json_schema().get("examples")
    assert ejemplos, f"{nombre} sin ejemplo"
    modelo.model_validate(ejemplos[0])


def test_los_ids_de_ruta_explican_de_donde_salen(client):
    params = client.get("/openapi.json").json()["paths"]["/consultas/{consulta_id}/recetas"]["post"]["parameters"]
    assert "POST /consultas" in params[0]["description"]


def test_los_modelos_de_salida_no_muestran_additional_props(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "additionalProperties" not in schemas["TutorOut"]


def test_los_ejemplos_del_recorrido_funcionan_de_extremo_a_extremo(client):
    """Los ejemplos prellenados de Swagger permiten recorrer RN-04 → 409 sin escribir JSON a mano."""
    ej = lambda n: getattr(s, n).model_json_schema()["examples"][0]  # noqa: E731
    h = DIR
    tutor = client.post("/tutores", json=ej("TutorIn"), headers=h)
    assert tutor.status_code == 201
    mascota = client.post("/pacientes", json={**ej("MascotaIn"), "tutor_id": tutor.json()["id"]}, headers=h).json()
    consulta = client.post("/consultas", json={**ej("ConsultaIn"), "paciente_id": mascota["id"]}, headers=h).json()
    assert client.post(f"/pacientes/{mascota['id']}/alergias", json=ej("AlergiaIn"), headers=h).status_code == 201
    assert client.post(f"/consultas/{consulta['id']}/recetas", json=ej("RecetaIn"), headers=h).status_code == 409
    hosp = client.post("/hospitalizaciones", json={**ej("HospitalizacionIn"), "paciente_id": mascota["id"]}, headers=h)
    assert hosp.status_code == 201
    orden = client.post("/ordenes", json=ej("OrdenIn"), headers=h)
    assert orden.status_code == 201


def test_pagina_docs_precarga_el_rol_y_la_raiz_redirige(client):
    html = client.get("/docs").text
    assert "preauthorizeApiKey('X-Rol', 'DIRECTOR')" in html and "persistAuthorization" in html
    assert "form-vc" in html and "Llena el formulario" in html  # formulario: un cuadro por dato
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/docs"

