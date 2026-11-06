"""Secciones HTML del reporte final (se completan con marcadores @@nombre@@ desde generar_reporte.py)."""

ANALISIS = """
<h1>2. Análisis del negocio (BRD)</h1>
<p>Fuente: BRD del equipo (U2), refinado en <code>docs/BRD.md</code>; los originales en PDF están en <code>docs/analisis/originales/</code>.</p>
<h2>2.1 Contexto y problema</h2>
<p><b>Modelo operativo.</b> VetCare 24 es una clínica y centro hospitalario veterinario con atención ininterrumpida (24/7): consultas generales y de especialidad, medicina preventiva, cirugía, laboratorio y hospitalización. Opera con cuenta familiar: un tutor puede tener varias mascotas y cada animal necesita un expediente individual, trazable e independiente.</p>
<p><b>Problema (AS-IS).</b> Registros físicos y digitales fragmentados: expedientes duplicados; consulta lenta de antecedentes y alergias en urgencias; calendarios de vacunación sin recordatorios; agenda con duraciones estáticas y sin carril de emergencia.</p>
<p><b>Visión (TO-BE).</b> Plataforma centralizada con expediente unificado tutor–mascotas, agenda por servicio, admisión inmediata de emergencias, notas inmutables con enmiendas auditadas y motor de recordatorios de vacunación.</p>
<h2>2.2 Stakeholders y actores</h2>
<table><tr><th>Actor</th><th>Responsabilidad</th><th>Necesidad principal</th><th>Rol en la API</th></tr>
<tr><td>Recepción</td><td>Admisión, cobros, agenda, primer contacto</td><td>Buscar rápido sin duplicar fichas; agendar según la duración real</td><td><code>RECEPCION</code></td></tr>
<tr><td>Médico veterinario</td><td>Diagnóstico, prescripción, cirugía, altas</td><td>Historial al instante, notas SOAP inmutables, alertas de alergia</td><td><code>VETERINARIO</code></td></tr>
<tr><td>Personal clínico / enfermería</td><td>Cuidados en piso y monitoreo</td><td>Capturar signos vitales en rondas periódicas</td><td><code>ENFERMERIA</code></td></tr>
<tr><td>Propietario / tutor</td><td>Responsable legal y financiero</td><td>Recordatorios de refuerzos; indicaciones de tratamiento</td><td>Receptor de notificaciones</td></tr>
<tr><td>Director médico / administrador</td><td>Supervisión, auditoría, gestión operativa</td><td>Auditar enmiendas; monitorear ocupación y cumplimiento de citas</td><td><code>DIRECTOR</code></td></tr></table>
<h2>2.3 Alcance</h2>
<table><tr><th>Dentro del alcance</th><th>Fuera del alcance</th></tr>
<tr><td>Gestión de identidad (tutor, mascotas, microchip) · Agenda inteligente por servicio (15/30/45/90–120 min) · Admisión de urgencia · Expediente clínico con bloqueo tras firma y enmiendas · Seguridad farmacológica por alergias · Módulo profiláctico (lote obligatorio, refuerzos 21/28/365 d, avisos) · Hospitalización 24/7 con bitácora y alta cruzada · RBAC por perfiles</td>
<td>Facturación electrónica ante entidades tributarias · Nómina y asistencia · Tienda virtual · Consultas por videollamada</td></tr></table>
<h2>2.4 Reglas de negocio</h2>
<table><tr><th>ID</th><th>Regla (BRD)</th><th>Dónde se hace cumplir</th></tr>
<tr><td><b>RN-01</b></td><td>Inmutabilidad médica: la nota firmada se congela; solo se corrige con Nota de Enmienda (autor, fecha, motivo)</td><td><code>Consulta._asegurar_editable</code>, <code>anexar_enmienda</code></td></tr>
<tr><td><b>RN-02</b></td><td>Prioridad de triage rojo: salta lista de espera y trámites administrativos</td><td><code>Consulta.admitir_urgencia</code></td></tr>
<tr><td><b>RN-03</b></td><td>Trazabilidad de biológicos: lote y fabricante obligatorios antes de guardar una vacuna</td><td><code>RegistroVacuna.aplicar</code></td></tr>
<tr><td><b>RN-04</b></td><td>Bloqueo por alergia registrada al recetar el mismo principio activo (excepción con justificación bajo cédula, ADR-002)</td><td><code>ServicioValidacionAlergias</code></td></tr>
<tr><td><b>RN-05</b></td><td>El expediente pertenece al animal: la transferencia conserva el historial y reasigna contacto y cobro</td><td><code>Paciente.transferir_a</code></td></tr>
<tr><td><b>RN-06</b></td><td>Validación cruzada de alta: liberar la jaula exige alta médica firmada y cuenta/precuenta liquidada</td><td><code>ServicioAltaHospitalaria</code>, <code>MAQUINA_HOSPITALIZACION</code></td></tr></table>
<h2>2.5 Requerimientos funcionales y no funcionales</h2>
<table><tr><th>ID</th><th>Requerimiento</th><th>Implementación / verificación</th></tr>
<tr><td>RF-01</td><td>Búsqueda predictiva por teléfono, mascota, código o microchip</td><td><code>GET /pacientes/buscar</code> · prueba US01/US12</td></tr>
<tr><td>RF-02</td><td>Hoja de triaje: peso, temperatura, motivo</td><td><code>POST /pacientes/{id}/triaje</code></td></tr>
<tr><td>RF-03</td><td>Citas con bloqueo automático por servicio</td><td><code>ServicioAgenda</code>, <code>POST /citas</code></td></tr>
<tr><td>RF-04</td><td>Cálculo automático del próximo refuerzo</td><td><code>RegistroVacuna.aplicar</code></td></tr>
<tr><td>RF-05</td><td>Recordatorio 48 h antes del refuerzo</td><td><code>RefuerzoPorNotificarSpec</code>, <code>POST /recordatorios/procesar</code></td></tr>
<tr><td>RF-06</td><td>Bitácora de constantes cada 2–4 h</td><td><code>Hospitalizacion.registrar_constantes</code></td></tr>
<tr><td>RNF-01</td><td>Expediente en menos de 3 s</td><td>prueba automatizada que mide el tiempo</td></tr>
<tr><td>RNF-02</td><td>Disponibilidad 24/7</td><td><code>/health</code>, <code>HEALTHCHECK</code>, despliegue gestionado</td></tr>
<tr><td>RNF-03</td><td>Acceso por roles; recepción sin detalle clínico</td><td><code>security.requiere</code>; pruebas 401/403</td></tr>
<tr><td>RNF-04</td><td>Vistas táctiles</td><td>No aplica a un backend REST (ver sección 12)</td></tr></table>
<h2>2.6 Criterios de éxito (KPIs)</h2>
<p>Duplicados &lt; 1 % · +40 % de retorno a refuerzos · ingreso de código rojo en &lt; 15 s · 100 % de bitácoras con intervalos ≤ 4 h. El sistema provee los datos y las reglas (<code>GET /reportes/operativo</code>, <code>LecturaVencidaSpec</code>); la medición real requiere operación en producción.</p>

<h1>3. Historias de usuario y criterios de aceptación (Gherkin)</h1>
<p>Las 15 historias del equipo (5 módulos) con su escenario Gherkin, el componente que lo implementa y la prueba que lo verifica.</p>
<table class="gh"><colgroup><col style="width:6%"><col style="width:27%"><col style="width:40%"><col style="width:27%"></colgroup><tr><th>US</th><th>Historia</th><th>Criterio de aceptación (Gherkin)</th><th>Implementación y prueba</th></tr>@@gh_rows@@</table>

<div class="land"><h1>4. Proceso de negocio (BPMN)</h1>

<div class="fig"><img src="@@bpmn@@" style="height:158mm;max-width:100%;object-fit:contain"><div class="cap">Figura 1. BPMN del proceso central de VetCare 24 (redibujado a partir del BPMN del equipo)</div></div></div>
<p>Proceso central de atención, internamiento y profilaxis, en tres carriles. Los objetos de datos DO_01…DO_04 corresponden a la ficha de admisión, el expediente electrónico, la receta con avisos y la bitácora hospitalaria. Las actividades sombreadas son las que materializan reglas de negocio.</p>
<table><tr><th>Actividad BPMN</th><th>Regla / historia</th><th>Componente</th></tr>
<tr><td>Botón «Admisión Urgencia» (Código Rojo)</td><td>RN-02 · US03</td><td><code>Consulta.admitir_urgencia</code> → <code>POST /urgencias</code></td></tr>
<tr><td>Búsqueda unificada + triaje (DO_01)</td><td>US12 · US04</td><td><code>PacienteRepository.buscar</code>, <code>Paciente.registrar_triaje</code></td></tr>
<tr><td>Asignación dinámica en agenda</td><td>US02 · RF-03</td><td><code>ServicioAgenda</code>, <code>SalaLibreSpec</code></td></tr>
<tr><td>Prescripción con validación contra alergias (DO_03)</td><td>RN-04 · US06</td><td><code>ServicioValidacionAlergias</code></td></tr>
<tr><td>Firmar y cerrar nota SOAP (DO_02)</td><td>RN-01 · US05 · US13</td><td><code>Consulta.firmar_y_cerrar</code>, <code>NotaEnmienda</code></td></tr>
<tr><td>Aplicación de biológico → refuerzo y recordatorio</td><td>RN-03 · US07 · US08</td><td><code>RegistroVacuna.aplicar</code>, <code>RefuerzoPorNotificarSpec</code></td></tr>
<tr><td>Asignación de jaula y fluidoterapia</td><td>US09</td><td><code>ServicioIngresoHospitalario</code></td></tr>
<tr><td>Monitoreo cada 2–4 h (DO_04)</td><td>RF-06 · US10</td><td><code>Hospitalizacion.registrar_constantes</code>, <code>LecturaVencidaSpec</code></td></tr>
<tr><td>Nota de egreso, auditoría de insumos y liquidación</td><td>RN-06 · US11</td><td><code>ServicioAltaHospitalaria</code>, <code>MAQUINA_HOSPITALIZACION</code></td></tr></table>

<h1>5. Glosario de dominio</h1>
<p>Los 20 términos del glosario del equipo y el elemento del modelo donde viven (lenguaje ubicuo: el código usa los mismos nombres).</p>
<table><tr><th>#</th><th>Término</th><th>Definición</th><th>En el modelo</th></tr>@@glos_rows@@</table>

<h1>6. Trazabilidad</h1>
<p>Cada regla, historia, escenario Gherkin y elemento BPMN se enlaza con su clase de dominio, su código y sus pruebas en <code>docs/TRAZABILIDAD.md</code> (24 filas), generado desde una tabla de datos. La prueba <code>test_trazabilidad.py</code> falla si algún archivo o símbolo citado ya no existe o si el documento está desactualizado, de modo que la matriz no puede desalinearse del código.</p>
<table><tr><th>Cadena</th><th>Ejemplo (RN-04)</th></tr>
<tr><td>BRD → User Story → Gherkin</td><td>RN-04 → US06 → «Bloqueo por prescripción de sustancia alérgena»</td></tr>
<tr><td>BPMN</td><td>Prescripción farmacológica (validación activa contra alergias, DO_03)</td></tr>
<tr><td>Dominio</td><td><code>ServicioValidacionAlergias</code>, <code>AlergenoCoincideSpec</code>, <code>BloqueoAlergiaDisparadoEvent</code></td></tr>
<tr><td>Código</td><td><code>services.py::ConsultaService</code> · <code>POST /consultas/{id}/recetas</code> (409)</td></tr>
<tr><td>Pruebas</td><td>unitarias del servicio de alergias + integración del endpoint (409 / 201 con justificación)</td></tr></table>
"""

PATRONES_H2 = """<h2>7.3 Patrones de diseño: selección y justificación</h2>
<table><tr><th>Patrón</th><th>Problema del negocio que resuelve</th><th>Dónde está</th><th>Alternativa descartada</th></tr>@@pat_rows@@</table>
"""

PRODUCCION = """<h1>9. Producción: Docker Compose, 12-Factor, CI/CD y despliegue</h1>
<table><tr><th>Requisito del PIA</th><th>Cómo se cumple</th><th>Evidencia</th></tr>
<tr><td>Docker Compose para DB + App + Tests</td><td><code>docker-compose.yml</code>: servicio <code>db</code> (PostgreSQL 16 con healthcheck), <code>app</code> (API en :8000, espera a la BD sana) y <code>tests</code> (pytest con cobertura; perfil <code>tests-pg</code> contra PostgreSQL). Imagen multi-etapa (base / test / app) con usuario sin privilegios y <code>HEALTHCHECK</code></td><td><code>docker compose up --build</code> · <code>docker compose run --rm tests</code></td></tr>
<tr><td>Variables de entorno (12-Factor)</td><td>Toda la configuración sale del entorno: <code>DATABASE_URL</code>, <code>SEED_ON_START</code>, <code>DATA_DIR</code>, <code>ENVIRONMENT</code>, <code>PORT</code>. <code>.env.example</code> sin secretos; <code>.env</code> excluido por <code>.gitignore</code> y <code>.dockerignore</code></td><td><code>.env.example</code>, <code>src/infrastructure/config.py</code></td></tr>
<tr><td>Pipeline CI/CD activo</td><td>GitHub Actions (<code>.github/workflows/ci.yml</code>): pytest contra un PostgreSQL de servicio con umbral de cobertura ≥ 80 %, exportación del OpenAPI, build de la imagen, pruebas dentro de Compose y deploy hook de Render</td><td>pestaña <i>Actions</i> del repositorio</td></tr>
<tr><td>Despliegue funcional</td><td><code>render.yaml</code> (Blueprint): base PostgreSQL + servicio web Docker con <code>SEED_ON_START=true</code> y <code>/health</code> como health check</td><td>URL pública (portada y README)</td></tr>
<tr><td>Swagger UI / OpenAPI activo</td><td>Swagger UI en <code>/docs</code> (en español, rol precargado y formulario por campos) y contrato en <code>/openapi.json</code>, exportado a <code>docs/api/openapi.json</code> en cada CI</td><td>Figuras 11 y 12</td></tr></table>
<div class="fig"><img src="@@sw1@@" style="width:70%"><div class="cap">Figura 11. Swagger UI en <code>/docs</code>: guía de uso y recorrido sugerido (captura local; sustituir por la del despliegue)</div></div>
<div class="fig"><img src="@@sw2@@" style="width:66%"><div class="cap">Figura 12. Una operación con formulario por campos, ejecutada con éxito (201): los datos viajan en la petición real</div></div>
"""

ANEXO = """
<h1>Anexo A. Cumplimiento de los requisitos del PIA</h1>
<table><tr><th>Criterio del documento del profesor</th><th>Evidencia en el repositorio</th><th>Sección</th></tr>
<tr><td>BRD completo y refinado de U2/U3</td><td><code>docs/BRD.md</code> + originales en <code>docs/analisis/originales/</code></td><td>2</td></tr>
<tr><td>≥ 15 User Stories con Gherkin, BPMN y glosario, con trazabilidad</td><td>15 historias; BPMN; 20 términos; <code>docs/TRAZABILIDAD.md</code></td><td>3, 4, 5, 6</td></tr>
<tr><td>Modelo/diagramas DDD (entidades, VO, agregados, servicios, eventos)</td><td>Diagramas de clases por agregado; 23 eventos de dominio; servicios de dominio</td><td>7.2, 7.4</td></tr>
<tr><td>UML consistente con la solución</td><td><code>docs/architecture/diagramas/*.png|.mmd</code> (derivados del código)</td><td>7.4</td></tr>
<tr><td>Patrones justificados</td><td>Tabla problema → patrón → alternativa descartada</td><td>7.3</td></tr>
<tr><td>SOLID demostrable</td><td><code>docs/architecture/SOLID.md</code> + prueba de regla de dependencia (AST)</td><td>7.5</td></tr>
<tr><td>ADRs: contexto, decisión, alternativas, consecuencias</td><td><code>docs/architecture/adr/ADR-001…006</code></td><td>7.6</td></tr>
<tr><td>Estructura del repositorio (docs/, src/ en 4 capas, tests/, .github/workflows, docker-compose.yml, .env.example, README)</td><td>Presentes tal como lo indica el documento</td><td>8</td></tr>
<tr><td>Código funcional: DDD + Specification + State Machine + API REST</td><td><code>src/domain</code>, <code>src/application</code>, <code>src/api</code></td><td>7, 8</td></tr>
<tr><td>Persistencia/DB, OpenAPI/Swagger, casos de uso integrales</td><td>SQLite/PostgreSQL; 38 rutas; recorrido en <code>/docs</code></td><td>8, 9</td></tr>
<tr><td>Pruebas unitarias e integración con cobertura ≥ 80 %</td><td>343 pruebas; 99.0 %</td><td>11</td></tr>
<tr><td>CI/CD activo en <code>.github/workflows/</code></td><td><code>ci.yml</code></td><td>9</td></tr>
<tr><td>Docker Compose reproducible (DB + App + Tests)</td><td><code>docker-compose.yml</code>, <code>Dockerfile</code></td><td>9</td></tr>
<tr><td>Variables de entorno + despliegue + Swagger en producción</td><td><code>.env.example</code>, <code>render.yaml</code>, <code>/docs</code></td><td>9</td></tr>
<tr><td>Demo en vivo y defensa técnica</td><td><code>docs/GUIA_DEFENSA.md</code> y presentación de apoyo</td><td>—</td></tr>
<tr><td>Historial de commits del equipo</td><td>Repositorio GitHub (commits de los tres integrantes)</td><td>Portada</td></tr></table>
"""
