"""Genera docs/Reporte_Final_VetCare24.pdf (HTML -> PDF con Chromium/Playwright). Uso: python scripts/generar_reporte.py"""
import html, json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "docs" / "evidencia"
evid = html.escape((EV / "evidencia.txt").read_text(encoding="utf-8"))
cob = html.escape((EV / "cobertura.txt").read_text(encoding="utf-8"))
import csv
from collections import Counter
with (ROOT / "data/resultados/casos_prueba_resultado.csv").open(encoding="utf-8-sig", newline="") as _f:
    _c = Counter((r["tipo_prueba"], r["resultado_alumno"].split(":")[0]) for r in csv.DictReader(_f))
valida, invalida = _c[("validar_operacion", "VALIDA")], _c[("validar_operacion", "INVALIDA")]
aplica, noaplica = _c[("evaluar_beneficio", "APLICA")], _c[("evaluar_beneficio", "NO_APLICA")]
assert valida + invalida == 60 and aplica + noaplica == 60
img = lambda n: (EV / n).as_uri()
DG = ROOT / 'docs' / 'architecture' / 'diagramas'
imgd = lambda n: (DG / n).as_uri()

US = [("US01", "Registro de propietario y mascotas", "PacienteService.registrar_mascota", "POST /pacientes"),
      ("US02", "Agendamiento diferenciado por servicio", "ServicioAgenda / Cita", "POST /citas"),
      ("US03", "Ingreso inmediato por triage de emergencia", "Consulta.admitir_urgencia", "POST /urgencias"),
      ("US04", "Signos vitales y alergias en admisión", "Paciente.registrar_triaje", "POST /pacientes/{id}/triaje"),
      ("US05", "Redacción y firma de nota de evolución", "Consulta.firmar_y_cerrar", "POST …/nota/firmar"),
      ("US06", "Prescripción segura (bloqueo por alergia)", "ServicioValidacionAlergias", "POST …/recetas"),
      ("US07", "Programación automática de refuerzos", "RegistroVacuna.aplicar", "POST /vacunas"),
      ("US08", "Envío de recordatorios 48 h antes", "RefuerzoPorNotificarSpec", "POST /recordatorios/procesar"),
      ("US09", "Ingreso a hospitalización", "ServicioIngresoHospitalario", "POST /hospitalizaciones"),
      ("US10", "Registro periódico de constantes", "Hospitalizacion.registrar_constantes", "POST …/constantes"),
      ("US11", "Alta hospitalaria y liquidación", "ServicioAltaHospitalaria", "POST …/alta-medica · …/liquidacion"),
      ("US12", "Búsqueda rápida de expediente", "PacienteRepository.buscar", "GET /pacientes/buscar"),
      ("US13", "Nota de enmienda / fe de erratas", "Consulta.anexar_enmienda", "POST …/enmiendas"),
      ("US14", "Solicitud y carga de laboratorio", "Consulta.adjuntar_resultado", "POST …/laboratorio"),
      ("US15", "Reporte operativo (ocupación, vacunas)", "ReporteService.operativo", "GET /reportes/operativo")]
us_rows = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td><code>{c}</code></td><td><code>{d}</code></td></tr>" for a, b, c, d in US)


import importlib.util, sys
sys.path.insert(0, str(ROOT / "scripts"))
from reporte_datos import GHERKIN, GLOSARIO, PATRONES
import reporte_html as RH
_sp = importlib.util.spec_from_file_location("trz", ROOT / "scripts" / "generar_trazabilidad.py"); _trz = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(_trz)
def _prueba(usid):
    for f in _trz.FILAS:
        if f[0].split(" / ")[0] == usid:
            return f[6][0].replace("tests/", "").replace("integration/", "").replace("unit/", "")
    return "—"
_impl = {a: (c, d) for a, b, c, d in US}
gh_rows = "".join(
    f"<tr><td><b>{i}</b></td><td>{como}</td><td><b>Escenario:</b> {esc}<br><b>Dado</b> {d}<br><b>Cuando</b> {c}<br><b>Entonces</b> {e}</td>"
    f"<td><code>{_impl[i][0]}</code><br><code>{_impl[i][1]}</code><br><small>Prueba: <code>{_prueba(i)}</code></small></td></tr>"
    for i, como, esc, d, c, e in GHERKIN)
glos_rows = "".join(f"<tr><td>{n}</td><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for n, (a, b, c) in enumerate(GLOSARIO, 1))
pat_rows = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in PATRONES)
def _fill(s):
    return (s.replace("@@gh_rows@@", gh_rows).replace("@@glos_rows@@", glos_rows).replace("@@pat_rows@@", pat_rows)
             .replace("@@bpmn@@", imgd("bpmn_proceso.png")).replace("@@sw1@@", img("swagger.png")).replace("@@sw2@@", img("swagger_formulario.png")))
ANALISIS, PATR, PROD, ANEXO = _fill(RH.ANALISIS), _fill(RH.PATRONES_H2), _fill(RH.PRODUCCION), _fill(RH.ANEXO)

CSS = """
@page{size:Letter;margin:22mm 18mm 20mm 18mm}
body{font-family:'DejaVu Sans',Arial,sans-serif;font-size:10pt;line-height:1.45;color:#1b2430}
h1{font-size:19pt;color:#0d4f4a;border-bottom:3px solid #0d4f4a;padding-bottom:4px;margin-top:26px;page-break-after:avoid}
h2{font-size:13pt;color:#0d4f4a;margin-top:18px;page-break-after:avoid} h3{font-size:11pt;margin-top:12px;page-break-after:avoid}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:8.8pt;page-break-inside:auto} tr{page-break-inside:avoid}
th{background:#0d4f4a;color:#fff;text-align:left;padding:4px 6px} td{border:1px solid #cfd8dc;padding:4px 6px;vertical-align:top}
code{font-family:'DejaVu Sans Mono',monospace;font-size:8.3pt;background:#eef3f3;padding:0 2px}
pre{font-family:'DejaVu Sans Mono',monospace;font-size:7pt;background:#101820;color:#d7e3e0;padding:8px;white-space:pre-wrap;word-break:break-word;border-radius:4px}
img{max-width:100%} .fig{text-align:center;margin:8px 0;page-break-inside:avoid} .cap{font-size:8.5pt;color:#566;margin-top:2px}
.cover{text-align:center;padding-top:70mm;page-break-after:always} .cover h1{border:none;font-size:28pt;margin:0}
.kpi{display:flex;gap:8px;margin:10px 0} .kpi div{flex:1;border:1px solid #cfd8dc;border-radius:6px;padding:8px;text-align:center}
.kpi b{display:block;font-size:17pt;color:#0d4f4a} .note{background:#fff7e0;border-left:4px solid #e0a800;padding:6px 10px;margin:8px 0}
.pb{page-break-before:always}
@page land{size:Letter landscape;margin:16mm 14mm 16mm 14mm} .land{page:land} .land h1{margin-top:0}
table.gh{table-layout:fixed} table.gh td{font-size:8pt;word-break:break-word} table.gh code{font-size:7.2pt}
"""

BODY = f"""


<h1>1. Resumen ejecutivo</h1>
<p>VetCare 24 es una clínica y hospital veterinario con atención 24/7. A partir del BRD, las 15 historias de usuario con Gherkin, el BPMN y el diseño DDD elaborados en las unidades 2 y 3,
se construyó una <b>API REST</b> en Python (FastAPI) con arquitectura limpia y <b>Domain Model</b> (ADR-001). Las seis reglas de negocio del BRD (RN-01…RN-06) viven en el dominio como
objetos que se protegen solos; se implementaron los patrones <b>Specification</b> (AND/OR/NOT), <b>State Machine</b> y <b>Domain Events</b>, persistencia relacional (SQLite/PostgreSQL),
contrato OpenAPI/Swagger, pruebas unitarias y de integración, contenedores Docker y CI/CD en GitHub Actions.</p>
<div class="kpi"><div><b>15 / 15</b>historias de usuario</div><div><b>6 / 6</b>reglas RN-01…06</div><div><b>343</b>pruebas automáticas</div><div><b>99.0 %</b>cobertura (dominio 100 %)</div><div><b>38</b>rutas OpenAPI</div></div>
<p>Además se resolvió el <b>paquete de datos</b> del caso (40 tutores, 20 servicios, 60 órdenes, 120 casos de prueba, 20 transiciones) y se validó con un <b>oráculo independiente</b> que no reutiliza el código del dominio.</p>

{ANALISIS}
<h1>7. Arquitectura</h1>
<h2>7.1 Decisión: Domain Model (ADR-001)</h2>
<p>Se comparó Transaction Script, Table Module y Domain Model. Se eligió <b>Domain Model (DDD)</b> porque las reglas RN-01…RN-06 son invariantes entrelazadas con ciclo de vida de estados: en un modelo rico el agregado las hace cumplir y se prueban sin base de datos ni servidor web.</p>
<div class="fig"><img src="{img('arq.png')}" style="width:100%"><div class="cap">Figura 2. Capas y regla de dependencia (api → application → domain ← infrastructure)</div></div>
<h2>7.2 Agregados y patrones</h2>
<table><tr><th>Agregado (raíz)</th><th>Invariantes</th></tr>
<tr><td>Paciente</td><td>microchip único; alergias sin duplicar; transferencia conserva historial</td></tr>
<tr><td>Consulta (SOAP, enmiendas, receta, estudios)</td><td>nota firmada inmutable; urgencia sin trámites; resultados de laboratorio se anexan sin editar la nota</td></tr>
<tr><td>Hospitalizacion + Jaula</td><td>lecturas cada 4 h (2 h en crítico); alta cruzada</td></tr>
<tr><td>RegistroVacuna</td><td>lote y marca obligatorios; refuerzo 21/28/365 días</td></tr>
<tr><td>Cita</td><td>duración por servicio (15/30/45/90–120 min), sala sin solapes, cancelación tardía &lt; 4 h</td></tr>
<tr><td>OrdenServicio (paquete de datos)</td><td><code>puede_procesarse</code>, beneficio de referencia, máquina de estados</td></tr></table>
<p>Los agregados se referencian solo por identificador (<code>paciente_id</code>, <code>tutor_id</code>), de modo que cada transacción modifica un único agregado.</p>
<ul><li><b>Specification</b> con <code>&amp;</code>, <code>|</code>, <code>~</code> y <code>reasons()</code>; p. ej. <code>puede_procesarse = TutorActivo &amp; OrdenConLineas &amp; OrdenAutorizada</code> y <code>beneficio = Preferente &amp; TotalMínimo &amp; ~Promoción</code>.</li>
<li><b>State Machine</b> por tabla (estado × acción → estado) para órdenes, hospitalización y citas; una transición inválida produce <code>InvalidStateTransition</code> (HTTP 409).</li>
<li><b>Domain Events</b> publicados <i>después</i> del commit (ADR-006); suscriptor activo: alerta al médico al recibir un resultado de laboratorio.</li>
<li><b>Repository + Unit of Work</b>; <b>Service Layer</b> delgada (solo orquesta).</li></ul>
<div class="fig"><img src="{img('estados.png')}" style="width:92%"><div class="cap">Figura 3. Máquina de estados de Hospitalizacion (RN-06)</div></div>
<div class="fig"><img src="{img('orden.png')}" style="width:92%"><div class="cap">Figura 4. Máquina de estados de OrdenServicio (paquete de datos)</div></div>
{PATR}<h2>7.4 Diagramas de clases del dominio (UML)</h2>
<p>El modelo se presenta por agregado (rombo lleno = composición dentro del agregado; flecha punteada = referencia por identificador a otro agregado). Todas las raíces heredan de <code>AggregateRoot</code>, que registra los eventos de dominio.</p>
<div class="fig"><img src="{imgd('clases_c1_paciente.png')}" style="width:100%"><div class="cap">Figura 5. Tutor y Paciente con sus Value Objects (RN-05)</div></div>
<div class="fig"><img src="{imgd('clases_c2_consulta.png')}" style="width:100%"><div class="cap">Figura 6. Consulta: nota SOAP, receta, enmiendas y laboratorio (RN-01, RN-02, RN-04)</div></div>
<div class="fig"><img src="{imgd('clases_c3_hospital.png')}" style="width:62%"><div class="cap">Figura 7. Hospitalización y Jaula (RN-06)</div></div>
<div class="fig"><img src="{imgd('clases_c4_otros.png')}" style="width:100%"><div class="cap">Figura 8. Vacunas (RN-03), Citas y Órdenes de servicio</div></div>
<div class="fig"><img src="{imgd('clases_c5_spec.png')}" style="width:92%"><div class="cap">Figura 9. Jerarquía de Specification</div></div>
<div class="fig"><img src="{imgd('clases_c6_estado.png')}" style="width:80%"><div class="cap">Figura 10. State Machine y servicios de dominio</div></div>
<h2>7.5 Principios SOLID</h2>
<table><tr><th>Principio</th><th>Aplicación en el código</th><th>Verificación</th></tr>
<tr><td><b>S</b> Responsabilidad única</td><td>Un agregado por conjunto de invariantes; un servicio de dominio por regla (<code>ServicioValidacionAlergias</code>, <code>ServicioIngresoHospitalario</code>, <code>ServicioAltaHospitalaria</code>); servicios de aplicación solo orquestan; controladores sin lógica</td><td>pruebas unitarias por pieza</td></tr>
<tr><td><b>O</b> Abierto/cerrado</td><td>Una regla nueva es una <code>Specification</code> nueva compuesta con <code>&amp;</code>, <code>|</code>, <code>~</code>; un estado nuevo es una fila de la tabla de <code>StateMachine</code>; un agregado nuevo es una subclase de <code>DocRepository</code></td><td><code>test_specification</code>, <code>test_state_machine</code></td></tr>
<tr><td><b>L</b> Sustitución de Liskov</td><td><code>And/Or/NotSpecification</code> sustituyen a <code>Specification</code>; cualquier <code>Notificador</code> o <code>EventBus</code> cumple el puerto; SQLite y PostgreSQL son intercambiables</td><td>suite completa en ambos motores; <code>test_arquitectura</code></td></tr>
<tr><td><b>I</b> Segregación de interfaces</td><td>Puertos pequeños y separados: <code>EventBus</code>, <code>Notificador</code>, <code>UnitOfWork</code></td><td><code>src/application/ports.py</code></td></tr>
<tr><td><b>D</b> Inversión de dependencias</td><td><code>application</code> depende de puertos; <code>infrastructure</code> los implementa; <code>api/container.py</code> es la única raíz de composición</td><td><code>test_arquitectura</code> analiza los <code>import</code> de todo <code>src/</code> y falla si una capa depende hacia afuera</td></tr></table>
<p>Detalle con fragmentos de código en <code>docs/architecture/SOLID.md</code>. Límites reconocidos: <code>UnitOfWork</code> expone sus repositorios sin tipar uno a uno, y algunos servicios de aplicación son grandes.</p>
<h2>7.6 Registros de decisión (ADR)</h2>
<p>Cada ADR documenta contexto, decisión, alternativas consideradas y consecuencias.</p>
<table><tr><th>ADR</th><th>Decisión</th></tr>
<tr><td>001</td><td>Domain Model / DDD con 4 agregados, servicios de dominio y Service Layer delgada (del equipo, U3)</td></tr>
<tr><td>002</td><td>Bloqueo por alergia con excepción justificada bajo cédula (RN-04)</td></tr>
<tr><td>003</td><td>Persistencia: un agregado = una fila (columnas indexadas + documento JSON/JSONB)</td></tr>
<tr><td>004</td><td>RBAC demostrativo por encabezado <code>X-Rol</code> (RNF-03)</td></tr>
<tr><td>005</td><td>Specification y State Machine explícitas</td></tr>
<tr><td>006</td><td>Eventos de dominio publicados solo tras el commit</td></tr></table>

<h1>8. Implementación</h1>
<table><tr><th>Aspecto</th><th>Detalle</th></tr>
<tr><td>Stack</td><td>Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, pytest + pytest-cov, PostgreSQL 16 / SQLite</td></tr>
<tr><td>Estructura</td><td><code>src/domain</code> · <code>src/application</code> · <code>src/infrastructure</code> · <code>src/api</code> · <code>tests</code> · <code>docs</code></td></tr>
<tr><td>Persistencia</td><td>Una tabla por agregado: columnas para consultar + columna <code>doc</code> (JSONB en PostgreSQL) serializada por un codec propio; el dominio no conoce el ORM</td></tr>
<tr><td>API</td><td>38 rutas (39 operaciones) en Swagger UI en español: cada recurso explica qué hace, su regla y los roles que pueden usarlo; los cuerpos traen ejemplos válidos y el rol DIRECTOR entra precargado; errores 400 (dato inválido) · 404 · 409 (regla de negocio / estado) · 422 (contrato); OpenAPI en <code>/openapi.json</code>, Swagger UI en <code>/docs</code></td></tr>
<tr><td>Seguridad</td><td>RBAC por rol (RECEPCION, VETERINARIO, ENFERMERIA, DIRECTOR) con encabezado <code>X-Rol</code> — <b>demostrativo, no es autenticación</b></td></tr>
<tr><td>Configuración</td><td>12-Factor: <code>DATABASE_URL</code>, <code>SEED_ON_START</code>, <code>DATA_DIR</code>, <code>ENVIRONMENT</code>, <code>PORT</code>; <code>.env.example</code> sin secretos</td></tr>
<tr><td>Contenedores</td><td><code>Dockerfile</code> multi-etapa (base / test / app, usuario sin privilegios, <code>HEALTHCHECK</code>); <code>docker-compose.yml</code> con servicios <i>db</i> (PostgreSQL), <i>app</i> y <i>tests</i></td></tr>
<tr><td>CI/CD</td><td>GitHub Actions: pruebas contra PostgreSQL de servicio, cobertura ≥ 80 %, exportación de OpenAPI, build de imagen, pruebas en Compose y <i>deploy hook</i> a Render</td></tr>
<tr><td>Despliegue</td><td><code>render.yaml</code> (Blueprint: PostgreSQL + servicio web Docker); Swagger UI en <code>/docs</code></td></tr></table>

{PROD}<h1>10. Paquete de datos VetCare 24</h1>
<p>Los CSV (40 tutores, 20 servicios, 60 órdenes con 117 líneas de detalle, 120 casos, 20 transiciones) se cargan con <code>SEED_ON_START=true</code> y se ejecutan contra el dominio real con <code>scripts/ejecutar_casos_prueba.py</code>.</p>
<table><tr><th>Regla evaluada</th><th>Resultado sobre las 60 órdenes</th></tr>
<tr><td><code>validar_operacion</code> (tutor activo AND ≥ 1 línea AND autorizada)</td><td>{valida} válidas · {invalida} inválidas</td></tr>
<tr><td><code>evaluar_beneficio</code> (preferente AND total ≥ 1 500 AND NOT promoción)</td><td>{aplica} aplican · {noaplica} no aplican</td></tr>
<tr><td>Transiciones (20)</td><td>aprobar/cancelar válidos; <code>completar</code> y <code>saltar_estado</code> desde SOLICITADA → 409; <code>repetir_aprobacion</code> → 409 en la 2.ª aprobación</td></tr></table>
<p><b>Oráculo independiente.</b> <code>test_oraculo_paquete_datos.py</code> recalcula cada total y cada veredicto únicamente con <code>csv</code> y <code>Decimal</code>, sin importar <code>src.domain</code>, y los compara contra las respuestas de la API: 120 casos + 20 transiciones. Así el código no se valida contra sí mismo.</p>
<div class="note">El <code>LEEME.txt</code> del paquete indica que sus reglas son ilustrativas y que las diferencias con el BRD deben documentarse. Ver <code>docs/DIFERENCIAS_PAQUETE_DATOS.md</code>
(p. ej. interpretación de estados terminales, seis órdenes históricas con un servicio deshabilitado, dos órdenes sin líneas).</div>

<h1>11. Evidencia de pruebas</h1>
<table><tr><th>Medición</th><th>Resultado</th></tr>
<tr><td>Pruebas automáticas</td><td><b>343 pasan</b> en SQLite en memoria y en PostgreSQL 16 real (<code>TEST_DATABASE_URL</code>)</td></tr>
<tr><td>Cobertura total</td><td><b>99.0 %</b> (requerido ≥ 80 %)</td></tr>
<tr><td>Por capa</td><td>dominio <b>100 %</b> · API 99.0 % · infraestructura 99.0 % · aplicación 96.3 %</td></tr>
<tr><td>Tipos</td><td>unitarias de dominio sin BD · integración vía API REST · oráculo del paquete de datos · trazabilidad verificada</td></tr></table>
<p>Hallazgo relevante: al ejecutar la suite contra PostgreSQL real se detectó que SQLAlchemy 2 interpreta <code>postgresql://</code> como el driver psycopg v3 mientras el proyecto usa psycopg2; habría fallado el despliegue.
Se corrigió con <code>normalizar_url</code> (que además convierte <code>postgres://</code> de Render) y quedó cubierto por pruebas.</p>
<h2>Cobertura por módulo (<code>pytest --cov=src</code>)</h2>
<pre>{cob}</pre>
<p>Reproducible con <code>docker compose run --rm tests</code> o <code>pytest --cov=src --cov-fail-under=80</code>; el pipeline de GitHub Actions ejecuta el mismo comando con ese umbral.</p>
<h2>Ejecución real de las reglas clave contra la API</h2>
<pre>{evid}</pre>

<h1>12. Diferencias, supuestos y limitaciones</h1>
<ul><li><b>Autenticación:</b> <code>X-Rol</code> es solo demostrativo; en producción se sustituye por JWT/OIDC en un único punto (<code>security.requiere</code>).</li>
<li><b>Notificaciones</b> (WhatsApp/correo) simuladas; el mensaje de recordatorio no incluye enlace para confirmar o reagendar (requiere cliente web).</li>
<li><b>Laboratorio:</b> se registra metadato y huella SHA-256 del archivo, no el binario.</li>
<li><b>Rangos de signos vitales</b> (temperatura 37.5–39.5 °C, FC 60–180, FR 10–40) y el esquema de refuerzo por edad son supuestos técnicos <b>pendientes de validación clínica</b> con el Director Médico.</li>
<li><b>US13:</b> el Gherkin menciona «consulta cerrada hace más de 24 h»; el BRD/ADR no fija plazo, por lo que se permite la enmienda en cualquier momento posterior a la firma.</li>
<li><b>Fuera de alcance:</b> consentimiento informado, lista de espera de cancelaciones, pago en línea de estudios externos, inventario de biológicos, interfaz gráfica y alertas sonoras.</li>
<li><b>KPIs de negocio</b> (duplicados &lt; 1 %, +40 % de retorno, código rojo &lt; 15 s) son métricas de operación en producción; el sistema provee los datos pero no pueden demostrarse con datos ficticios.</li></ul>

<h1>13. Conclusiones</h1>
<p>El Domain Model resultó adecuado: las reglas más delicadas (alergias, inmutabilidad, alta cruzada) quedaron concentradas en pocos métodos de dominio, probados al 100 % sin infraestructura,
y la capa de aplicación se mantuvo como orquestadora. Specification y State Machine hicieron que las reglas del paquete de datos fueran explicables (cada rechazo nombra la regla incumplida) y verificables con un oráculo independiente.
Probar sobre PostgreSQL real, y no solo SQLite, evitó un fallo de despliegue. La trazabilidad verificada por pruebas reduce el riesgo de documentación desalineada con el código.</p>
<p><b>Trabajo futuro:</b> autenticación real; adaptador de mensajería; almacenamiento de archivos; consentimiento informado y lista de espera; validación clínica de rangos; cliente web/tablet responsivo (RNF-04); observabilidad.</p>

<h2>Referencias</h2>
<p>FIME UANL. (2026). <i>Caso 04: VetCare 24</i> (Unidad 2: Análisis de Requerimientos de Negocio). · Fowler, M. (2002). <i>Patterns of Enterprise Application Architecture</i>. Addison-Wesley. · Evans, E. (2003). <i>Domain-Driven Design</i>. Addison-Wesley.
· Documentos del equipo (U2/U3) en <code>docs/analisis/originales/</code>.</p>
{ANEXO}
"""

html_doc = f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{BODY}</body></html>"
(ROOT / "docs" / "Reporte_Final_VetCare24.html").write_text(html_doc, encoding="utf-8")
import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reporte_portada import HTML as PORTADA, plantillas
cab, pie = plantillas()
cuerpo_pdf, portada_pdf = ROOT / "docs" / "_cuerpo.pdf", ROOT / "docs" / "_portada.pdf"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto((ROOT / "docs" / "Reporte_Final_VetCare24.html").as_uri()); pg.wait_for_timeout(800)
    pg.pdf(path=str(cuerpo_pdf), prefer_css_page_size=True, print_background=True, display_header_footer=True,
           header_template="<div style='font-size:7pt;width:100%;text-align:right;padding-right:14mm;color:#789'>VetCare 24 — Equipo 4 · FIME-UANL</div>",
           footer_template="<div></div>")
    pg2 = b.new_page(); pg2.set_content(PORTADA); pg2.wait_for_timeout(500)
    pg2.pdf(path=str(portada_pdf), prefer_css_page_size=True, print_background=True, display_header_footer=True,
            header_template=cab, footer_template=pie)
    b.close()
w = PdfWriter()
for f in (portada_pdf, cuerpo_pdf):
    for pagina in PdfReader(str(f)).pages:
        w.add_page(pagina)
total, n_portada = len(w.pages), len(PdfReader(str(portada_pdf)).pages)
for k, pagina in enumerate(w.pages, 1):
    if k <= n_portada:
        continue
    ancho, alto = float(pagina.mediabox.width), float(pagina.mediabox.height)
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(ancho, alto)); c.setFont("Helvetica", 7.5); c.setFillGray(0.5)
    c.drawCentredString(ancho / 2, 16, f"{k} / {total}"); c.save(); buf.seek(0)
    pagina.merge_page(PdfReader(buf).pages[0])
w.add_metadata({"/Title": "VetCare 24 — Reporte final PIA (Equipo 4)", "/Author": "Equipo 4 · FIME-UANL"})
with open(ROOT / "docs" / "Reporte_Final_VetCare24.pdf", "wb") as fh:
    w.write(fh)
cuerpo_pdf.unlink(); portada_pdf.unlink()
print("ok", total, "páginas")
