"""Páginas iniciales del reporte con el formato de los reportes del curso (logos UANL/FIME, tabla de datos,
bibliografía APA, propósito e introducción). Se unen al cuerpo del reporte en generar_reporte.py."""
import base64
from pathlib import Path

LOGOS = Path(__file__).resolve().parents[1] / "docs" / "evidencia" / "logos"


def _b64(nombre):
    return "data:image/png;base64," + base64.b64encode((LOGOS / nombre).read_bytes()).decode()


CSS = """
@page{size:Letter;margin:38mm 30mm 28mm 30mm}
body{font-family:'Carlito','Calibri',Arial,sans-serif;font-size:11.5pt;line-height:1.42;color:#000;margin:0}
table.datos{border-collapse:collapse;width:100%;font-family:'Liberation Sans',Arial,sans-serif;font-size:11.5pt}
table.datos td{border:1px solid #000;padding:6px 8px;vertical-align:top}
table.datos p{margin:0 0 7px 0} table.datos p:last-child{margin-bottom:0}
.apa p{font-size:9.6pt;line-height:1.3;margin:0 0 6px 0;padding-left:0}
h2{font-size:14pt;font-weight:700;margin:0 0 8px 0;page-break-after:avoid}
p.t{text-align:justify;margin:0 0 11px 0} .pb{page-break-before:always}
code{font-family:Consolas,'DejaVu Sans Mono',monospace;font-size:10pt}
"""

REFS = [
    "Facultad de Ingeniería Mecánica y Eléctrica. (2026). <i>Producto Integrador de Aprendizaje: Proyecto final — Implementación de una solución de software basada en lógica de negocio</i> [Documento del curso]. Universidad Autónoma de Nuevo León.",
    "Equipo 4. (2026). <i>VetCare 24: Documento de requerimientos de negocio (BRD), historias de usuario con Gherkin, BPMN y glosario</i> [Documentos de las Unidades 2 y 3]. Facultad de Ingeniería Mecánica y Eléctrica, UANL.",
    "Evans, E. (2003). <i>Domain-driven design: Tackling complexity in the heart of software</i>. Addison-Wesley Professional.",
    "Fowler, M. (2002). <i>Patterns of enterprise application architecture</i>. Addison-Wesley Professional.",
    "Nygard, M. (2011, 15 de noviembre). <i>Documenting architecture decisions</i> [Entrada de blog]. Cognitect. https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions",
    "Okken, B. (2022). <i>Python testing with pytest: Simple, rapid, effective, and scalable</i> (2.ª ed.). Pragmatic Bookshelf.",
    "Wiggins, A. (2017). <i>The twelve-factor app</i>. https://12factor.net/es/",
]

HTML = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<table class="datos">
<tr><td style="width:72%"><p><b>Nombres: Equipo 4</b></p><p><b>Giovani Aldahir Patiño Rodriguez</b></p><p><b>Aldo Rene Romero Parga</b></p><p><b>Leonardo Alonso Muñiz Espinosa</b></p></td>
<td><p><b>Matrículas:</b></p><p>2118917</p><p>2118748</p><p>2115635</p></td></tr>
<tr><td colspan="2" style="padding:0"><table style="width:100%;border-collapse:collapse"><tr>
<td style="width:50%;border:0;border-right:1px solid #000"><b>Nombre del curso:</b> Componentes de Lógica de Negocio</td>
<td style="border:0"><b>Nombre del profesor:</b> Miguel Ángel Gómez Marroquín</td></tr></table></td></tr>
<tr><td colspan="2" style="padding:0"><table style="width:100%;border-collapse:collapse"><tr>
<td style="width:50%;border:0;border-right:1px solid #000"><b>Modulo Netacad:</b> PIA (Proyecto Final)</td>
<td style="border:0"><b>Actividad:</b> PIA. Implementación de una solución de software basada en lógica de negocio · VetCare 24</td></tr></table></td></tr>
<tr><td colspan="2"><b>Fecha:</b> 06/11/2026</td></tr>
<tr><td colspan="2"><b>Repositorio:</b> https://github.com/&lt;USUARIO&gt;/&lt;REPO&gt; &nbsp;·&nbsp; <b>API desplegada (Swagger UI):</b> https://&lt;SERVICIO&gt;.onrender.com/docs</td></tr>
<tr><td colspan="2" class="apa"><p style="font-size:11.5pt;font-family:'Liberation Sans',Arial,sans-serif"><b>Bibliografía (Formato APA)</b></p>{''.join(f'<p>{r}</p>' for r in REFS)}</td></tr>
</table>

<div class="pb"></div>
<h2>Propósito de la Actividad</h2>
<p class="t">El propósito de este proyecto integrador es convertir el análisis y el diseño de VetCare 24 (BRD, historias de usuario con criterios Gherkin, BPMN, glosario y decisiones de arquitectura de las unidades 2 y 3) en una solución de software funcional, verificable y desplegable. La meta es que cada regla de negocio pueda rastrearse desde el documento de requerimientos hasta el código que la hace cumplir y la prueba automática que la comprueba, y no solo afirmar que «el programa corre».</p>
<p class="t">Para lograrlo se construyó una API REST con Domain-Driven Design, Specification y State Machine; se escribieron pruebas unitarias y de integración con una cobertura muy superior al 80 % exigido; se contenerizó la solución con Docker Compose (base de datos, aplicación y pruebas); se separó la configuración del código mediante variables de entorno; y se automatizó la verificación con un pipeline de GitHub Actions y un despliegue con Swagger UI activo para la demostración.</p>

<h2 style="margin-top:18px">Introducción</h2>
<p class="t">VetCare 24 es una clínica y hospital veterinario con atención 24/7 cuyo problema original eran los registros fragmentados: expedientes duplicados, consulta lenta de alergias en urgencias, vacunas sin recordatorios y una agenda que no distingue un procedimiento breve de una cirugía. En las unidades anteriores el trabajo se centró en entender el negocio, documentar sus reglas y diseñar el dominio. En este proyecto el reto cambia: hay que demostrar que el código respeta esas reglas, sobre todo en los casos límite, donde suelen esconderse los defectos más caros.</p>
<p class="t">A partir de los artefactos del equipo se implementaron las 15 historias de usuario y las seis reglas de negocio RN-01 a RN-06 (inmutabilidad de la nota médica, prioridad del triage rojo, trazabilidad de biológicos, bloqueo por alergia, propiedad del historial y alta hospitalaria cruzada). Se resolvió además el paquete de datos del profesor (40 tutores, 20 servicios, 60 órdenes y 120 casos de prueba) y se validó con un oráculo independiente que no reutiliza el código del dominio. Al ejecutar las pruebas contra PostgreSQL real se detectó y corrigió un defecto de despliegue que SQLite no mostraba.</p>
<p class="t">El reporte se organiza en el orden que pide el documento del proyecto: análisis del negocio (BRD, historias y Gherkin, BPMN, glosario y trazabilidad), arquitectura (DDD, patrones, SOLID, UML y ADRs), implementación y producción (Docker, variables de entorno, CI/CD y despliegue), paquete de datos, evidencias de pruebas, limitaciones y conclusiones. Al final se incluye un anexo que relaciona cada criterio de evaluación con su evidencia en el repositorio.</p>
</body></html>"""


def plantillas():
    """Encabezado (logos UANL y FIME + «Reporte») y pie (logo «unidos») iguales a los reportes del curso."""
    cab = (f"<div style=\"width:100%;box-sizing:border-box;padding:0 30mm;margin-top:9mm;display:flex;justify-content:space-between;align-items:flex-start;font-family:Arial\">"
           f"<img src=\"{_b64('uanl.png')}\" style=\"height:15mm\">"
           f"<div style=\"text-align:right\"><img src=\"{_b64('fime.png')}\" style=\"height:15mm\"><div style=\"font-size:8pt;margin-top:1mm\">Reporte</div></div></div>")
    pie = (f"<div style=\"width:100%;box-sizing:border-box;padding:0 30mm;text-align:right\"><img src=\"{_b64('unidos.png')}\" style=\"height:11mm\"></div>")
    return cab, pie
