"""Documentación de la API (Swagger UI / OpenAPI) en lenguaje llano.

Aquí vive solo texto: ningún endpoint cambia su comportamiento. Los roles de cada recurso se leen de las
dependencias reales (`security.requiere`), de modo que la documentación no puede desincronizarse del código.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

ROL_POR_OMISION_EN_DOCS = "DIRECTOR"

DESCRIPCION = """
API REST de **VetCare 24**, clínica y hospital veterinario 24/7 (PIA de Componentes de Lógica de Negocios, FIME-UANL, Equipo 4).
Cada recurso aplica una regla del negocio definida en el BRD, las User Stories y el BPMN (**RN-01 … RN-06**).

## Cómo usar cada operación (3 pasos)
1. **Abre** una operación haciendo clic en su barra de color (por ejemplo `POST /tutores`).
2. **Llena el formulario**: un cuadro por dato (nombre, teléfono, etc.), todos marcados en **azul** y ya con un ejemplo válido. Si la operación pide un `id` en *Parámetros*, pégalo ahí: es el `id` que devolvió el paso anterior. Luego pulsa **▶ Ejecutar**.
3. **Lee el resultado** en *Respuesta del servidor*, justo debajo: código **2xx** = funcionó; **4xx** = algo falló y el mensaje dice qué. Lo que aparece más abajo en gris (*Ejemplo*) es solo documentación, no tu resultado.

El rol ya viene elegido (`DIRECTOR`, puede usar todo). Para cambiarlo pulsa **Autorizar** (arriba a la derecha).

## Recorrido sugerido (cada paso usa el `id` que devolvió el anterior)
| # | Recurso | Qué demuestra |
|---|---|---|
| 1 | `POST /tutores` → `POST /pacientes` | Alta de tutor y mascota (US01) |
| 2 | `POST /pacientes/{id}/alergias` | Registrar alergia a *penicilina* |
| 3 | `POST /consultas` | Abrir consulta con cédula del veterinario |
| 4 | `POST /consultas/{id}/recetas` | **409 RN-04**: bloqueo por alergia |
| 5 | misma receta + `justificacion` y `cedula_justificante` | **201**: excepción clínica (ADR-002) |
| 6 | `PUT …/nota` → `POST …/nota/firmar` | Redactar y firmar la nota SOAP (US05) |
| 7 | `PUT …/nota` otra vez | **409 RN-01**: una nota firmada no se edita |
| 8 | `POST …/enmiendas` | **201**: la corrección va como nota de enmienda (US13) |
| 9 | `POST /hospitalizaciones` (jaula `JP-01`) | Ingreso a hospitalización (US09) |
| 10 | `POST …/alta-medica` → `POST …/liquidacion` | **RN-06**: la jaula se libera solo con alta firmada **y** cuenta liquidada |
| 11 | `GET /ordenes/VET-O001` → `POST …/transiciones` | Datos del profesor, Specification y State Machine |

## Códigos de respuesta
**201** creado · **200** correcto · **400** dato inválido · **401** falta o es desconocido el rol · **403** el rol no tiene acceso (RNF-03) ·
**404** el id no existe · **409** regla de negocio o estado no permitido · **422** el JSON no cumple el contrato.
Los errores de negocio responden `{"codigo": "...", "mensaje": "..."}` con el motivo exacto.

## Datos que conviene saber
- Importes y pesos viajan como **texto** (`"7587.00"`) para no perder precisión.
- Con `SEED_ON_START=true` ya existen los datos del profesor: tutor `VET-C012`, servicios `VET-P001…`, órdenes `VET-O001…` y las 20 jaulas (`JP-01…`, `JG-01…`, `JA-01…`).
- La autenticación por `X-Rol` es una **demostración** (ADR-004); en producción se reemplaza por JWT sin tocar el dominio.
"""

TAGS: list[dict[str, str]] = [
    {"name": "1 · Tutores y mascotas", "description": "Registro de tutores y pacientes, búsqueda y transferencia de titularidad (US01, US12, RN-05)."},
    {"name": "2 · Triaje y urgencias", "description": "Triaje, alergias y admisión de emergencia Código Rojo (US03, US04, RN-02)."},
    {"name": "3 · Consultas y expediente", "description": "Consulta, nota SOAP, receta con bloqueo por alergia, enmiendas y laboratorio (US05, US06, US13, US14, RN-01, RN-04)."},
    {"name": "4 · Vacunas y recordatorios", "description": "Aplicación de vacunas con lote y marca, refuerzos y avisos 48 h antes (US07, US08, RN-03)."},
    {"name": "5 · Citas", "description": "Agenda con duración por servicio, sala sin solapes y cancelación (US02)."},
    {"name": "6 · Hospitalización", "description": "Jaulas, ingreso, constantes vitales, precuenta y alta cruzada (US09, US10, US11, RN-06)."},
    {"name": "7 · Órdenes de servicio", "description": "Paquete de datos del profesor: Specification (AND/OR/NOT) y máquina de estados de la orden."},
    {"name": "8 · Reportes", "description": "KPIs de ocupación, vacunación y citas canceladas para el Director (US15)."},
    {"name": "9 · Operación", "description": "Estado del servicio."},
]

# (método, ruta) -> (resumen corto, explicación). Los roles se agregan solos desde el código.
DOCS: dict[tuple[str, str], tuple[str, str]] = {
    ("GET", "/health"): ("Verificar que el servicio está vivo",
                         "No requiere rol. Lo usa la plataforma de despliegue para saber que la API arrancó."),
    # ---- 1
    ("POST", "/tutores"): ("Registrar un tutor",
                           "Crea al responsable de una mascota. Exige **teléfono o correo** de contacto.\n\nResultado: el `id` (`TUT-…`) se usa en `POST /pacientes`."),
    ("GET", "/tutores/{tutor_id}"): ("Consultar un tutor",
                                     "Devuelve el tutor. Prueba con `VET-C012` (viene en los datos del profesor)."),
    ("POST", "/pacientes"): ("Registrar una mascota (US01)",
                             "Crea el expediente (`EXP-…`). `especie` es PERRO, GATO u OTRO. El microchip, si se manda, debe ser único.\n\nResultado: el `id` (`PAC-…`) se usa en casi todos los demás recursos."),
    ("GET", "/pacientes/buscar"): ("Buscar mascotas por nombre, microchip, expediente o dueño (US12)",
                                   "Búsqueda predictiva: escribe al menos 2 letras en `q` (nombre de la mascota o del tutor, teléfono del tutor, microchip o código de expediente)."),
    ("GET", "/pacientes/{paciente_id}"): ("Consultar una mascota",
                                          "Datos generales y alertas de alergia. No incluye información clínica (eso es el expediente)."),
    ("GET", "/pacientes/{paciente_id}/expediente"): ("Ver el expediente clínico completo",
                                                     "**RNF-03:** solo personal médico. Si entras como `RECEPCION` responde **403**: es la forma más rápida de demostrar el control de acceso."),
    ("POST", "/pacientes/{paciente_id}/transferencia"): ("Transferir la titularidad a otro tutor (RN-05)",
                                                         "El historial clínico **pertenece al animal**: cambia el responsable, el expediente se conserva intacto. `nuevo_tutor_id` debe existir y estar activo."),
    # ---- 2
    ("POST", "/pacientes/{paciente_id}/triaje"): ("Capturar el triaje inicial (US04)",
                                                  "Actualiza peso y alergias del perfil y deja la hoja de triaje en el expediente. La temperatura debe estar entre 30 y 45 °C."),
    ("POST", "/pacientes/{paciente_id}/alergias"): ("Registrar una alergia",
                                                    "Agrega un principio activo (en minúsculas, sin duplicar). A partir de aquí **RN-04** bloqueará recetas con ese principio."),
    ("POST", "/urgencias"): ("Admitir una emergencia Código Rojo (US03, RN-02)",
                             "Abre una consulta urgente **sin exigir trámites administrativos** (sin paciente ni datos del tutor). Mientras no se regularice no puede recetar ni pedir estudios."),
    ("POST", "/urgencias/{consulta_id}/regularizar"): ("Asignar el paciente a una urgencia ya atendida",
                                                       "Completa la parte administrativa después de estabilizar al animal. Manda `paciente_id` como parámetro de la URL."),
    # ---- 3
    ("POST", "/consultas"): ("Abrir una consulta",
                             "Une al paciente con el veterinario que lo atiende (cédula profesional). Resultado: el `id` (`CON-…`) para receta, nota y laboratorio."),
    ("GET", "/consultas/{consulta_id}"): ("Consultar una consulta", "Nota, receta, enmiendas y estudios de laboratorio."),
    ("PUT", "/consultas/{consulta_id}/nota"): ("Redactar o editar la nota SOAP",
                                               "Subjetivo, Objetivo, Análisis y Plan. **RN-01:** si la nota ya está firmada responde **409** `NotaInmutableError`; solo se admite una enmienda."),
    ("POST", "/consultas/{consulta_id}/nota/firmar"): ("Firmar y cerrar la nota (US05, RN-01)",
                                                       "Con la cédula del veterinario la nota queda **congelada** para siempre."),
    ("POST", "/consultas/{consulta_id}/enmiendas"): ("Anexar una nota de enmienda (US13)",
                                                     "La forma correcta de corregir una nota firmada: la original no cambia, la enmienda queda anexa con motivo, detalle y cédula."),
    ("POST", "/consultas/{consulta_id}/recetas"): ("Prescribir un medicamento (US06, RN-04)",
                                                   "Si el principio activo coincide con una alergia del paciente responde **409** `AlergiaBloqueoError`.\n\n"
                                                   "Para continuar de todos modos manda `justificacion` y `cedula_justificante` (excepción clínica, ADR-002): responde **201**."),
    ("POST", "/consultas/{consulta_id}/laboratorio"): ("Solicitar un estudio de laboratorio (US14)",
                                                       "Registra la petición. Resultado: el `id` del estudio (`estudios[].id`) que se usa para adjuntar el resultado."),
    ("POST", "/consultas/{consulta_id}/laboratorio/{estudio_id}/resultado"): ("Adjuntar el resultado y avisar al médico (US14)",
                                                                              "Guarda el nombre del archivo y su huella SHA-256 (no el archivo). Se dispara un evento que **alerta al médico tratante**."),
    # ---- 4
    ("POST", "/vacunas"): ("Registrar una vacuna aplicada (US07, RN-03)",
                           "**RN-03:** `lote` y `marca` son obligatorios; sin ellos responde 400. Calcula solo la fecha del refuerzo (21, 28 o 365 días según el esquema o la edad)."),
    ("POST", "/recordatorios/procesar"): ("Enviar los recordatorios de refuerzo pendientes (US08)",
                                          "Avisa por el canal preferido del tutor (WhatsApp o correo) a quienes tienen refuerzo en ~48 h. Los envíos son **simulados** y quedan registrados."),
    # ---- 5
    ("POST", "/citas"): ("Agendar una cita (US02)",
                         "La duración y la sala dependen del servicio: vacuna 15 min, consulta 30, especialidad 45, cirugía 90–120 (quirófano). **409** si no hay sala libre o la fecha ya pasó. `inicio` en ISO 8601."),
    ("GET", "/citas"): ("Ver las citas de un día", "Indica la fecha en `dia` (AAAA-MM-DD)."),
    ("GET", "/citas/{cita_id}"): ("Consultar una cita", "Incluye `acciones_permitidas` según su estado."),
    ("POST", "/citas/{cita_id}/cancelar"): ("Cancelar una cita (US02)",
                                            "Libera la sala. Si faltan **menos de 4 h** se marca `cancelacion_tardia` (cuenta en los KPIs)."),
    # ---- 6
    ("GET", "/jaulas"): ("Listar las jaulas", "`libres=true` muestra solo las desocupadas. Hay 12 de perro (`JP-`), 6 de gato (`JG-`) y 2 de aislamiento (`JA-`)."),
    ("POST", "/hospitalizaciones"): ("Ingresar a un paciente a hospitalización (US09)",
                                     "Asigna la jaula. **409** si está ocupada, si no corresponde a la especie o si se mezcla un paciente contagioso fuera de aislamiento (y al revés)."),
    ("GET", "/hospitalizaciones/alertas/lecturas-vencidas"): ("Pacientes con constantes vitales vencidas (US10)",
                                                              "Lista a quienes no tienen lectura dentro de la ventana: **4 h** si están estables, **2 h** si están críticos."),
    ("GET", "/hospitalizaciones/{hid}"): ("Consultar una hospitalización", "Estado, bitácora, precuenta y si ya es `apto_para_egreso`."),
    ("POST", "/hospitalizaciones/{hid}/constantes"): ("Registrar constantes vitales (US10)",
                                                      "Una lectura fuera de rango marca al paciente como CRÍTICO (ventana de 2 h) hasta que una lectura vuelva a ser normal."),
    ("POST", "/hospitalizaciones/{hid}/consumos"): ("Agregar un consumo a la precuenta", "Suma medicamentos o servicios al total que se liquidará al egreso."),
    ("POST", "/hospitalizaciones/{hid}/alta-medica"): ("Alta cruzada, paso 1: firma del veterinario (US11, RN-06)",
                                                       "Responde `PENDIENTE_VALIDACION_CRUZADA`: la jaula **sigue ocupada** hasta que recepción liquide la cuenta."),
    ("POST", "/hospitalizaciones/{hid}/liquidacion"): ("Alta cruzada, paso 2: liquidación en recepción (US11, RN-06)",
                                                       "Si el alta ya estaba firmada responde `EGRESO_CONCLUIDO` y la jaula queda libre. El orden de los dos pasos no importa; se necesitan **ambos**."),
    # ---- 7
    ("GET", "/servicios"): ("Catálogo de servicios del profesor", "Precio, capacidad y si está habilitado (`VET-P001…`)."),
    ("POST", "/ordenes"): ("Solicitar una orden de servicio",
                           "Valida cantidades, capacidad y disponibilidad. Devuelve el total, si `puede_procesarse` (Specification `TutorActivo & OrdenConLineas & OrdenAutorizada`) y por qué no, en `motivos_no_procesable`."),
    ("GET", "/ordenes/{orden_id}"): ("Consultar una orden", "Prueba con `VET-O001`: total `7587.00` y `puede_procesarse: true`."),
    ("POST", "/ordenes/{orden_id}/transiciones"): ("Cambiar el estado de la orden (State Machine)",
                                                   "`aprobar` (SOLICITADA→CONFIRMADA), `completar` (CONFIRMADA→REALIZADA) o `cancelar`. Una acción que no corresponde al estado actual responde **409** `InvalidStateTransition`."),
    # ---- 8
    ("GET", "/reportes/operativo"): ("Indicadores operativos (US15)",
                                     "Ocupación de jaulas, vacunas aplicadas y citas canceladas (con las tardías) en el periodo. Sin fechas usa los últimos 7 días."),
}

# Descripción y ejemplo de los parámetros de ruta, para que Swagger diga de dónde sale cada id.
PARAMETROS: dict[str, tuple[str, str]] = {
    "tutor_id": ("`id` del tutor (lo devuelve POST /tutores). Con los datos del profesor: VET-C012", "VET-C012"),
    "paciente_id": ("`id` de la mascota (lo devuelve POST /pacientes)", "PEGA-AQUI-EL-ID-DE-LA-MASCOTA"),
    "consulta_id": ("`id` de la consulta (lo devuelve POST /consultas o POST /urgencias)", "PEGA-AQUI-EL-ID-DE-LA-CONSULTA"),
    "estudio_id": ("`id` del estudio, dentro de `estudios` de la consulta", "PEGA-AQUI-EL-ID-DEL-ESTUDIO"),
    "cita_id": ("`id` de la cita (lo devuelve POST /citas)", "PEGA-AQUI-EL-ID-DE-LA-CITA"),
    "hid": ("`id` de la hospitalización (lo devuelve POST /hospitalizaciones)", "PEGA-AQUI-EL-ID-DE-LA-HOSPITALIZACION"),
    "orden_id": ("`id` de la orden. Con los datos del profesor: VET-O001", "VET-O001"),
}


def _roles_de(route: Any) -> tuple[str, ...] | None:
    for dep in getattr(route, "dependencies", []) or []:
        roles = getattr(dep.dependency, "roles", None)
        if roles:
            return roles
    return None


def aplicar_documentacion(*rutas: Any) -> None:
    """Pone resumen, explicación y roles a cada ruta (antes de generar el OpenAPI). Es idempotente.

    Recibe los objetos con `.routes` (la app y el router): FastAPI ≥ 0.16 no expone las rutas de un router
    incluido en `app.routes`, por eso se documenta cada origen por separado.
    """
    for route in (r for origen in rutas for r in origen.routes):
        for metodo in getattr(route, "methods", None) or ():
            clave = (metodo, route.path)
            if clave not in DOCS:
                continue
            resumen, texto = DOCS[clave]
            route.summary = resumen
            roles = _roles_de(route)
            acceso = ("**Roles con acceso:** " + ", ".join(f"`{r}`" for r in roles)) if roles else "**Roles con acceso:** cualquiera (no requiere `X-Rol`)."
            route.description = f"{texto}\n\n{acceso}"
            route.response_description = "Creado correctamente" if route.status_code == 201 else "Correcto"


def instalar_openapi(app: FastAPI) -> None:
    """Agrega descripciones a los parámetros de ruta al generar el esquema OpenAPI (una sola vez)."""
    original = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        esquema = original()
        for operaciones in esquema.get("paths", {}).values():
            for op in operaciones.values():
                for par in op.get("parameters", []):
                    if par.get("in") == "path" and par["name"] in PARAMETROS:
                        par["description"], ejemplo = PARAMETROS[par["name"]]
                        par["example"] = ejemplo
        return esquema

    app.openapi = openapi  # type: ignore[method-assign]


_TRADUCCION = "\n    const _ES = {\n        'Parameters': 'Parámetros (llena los cuadros azules)', 'Request body': 'Datos a enviar (JSON)',\n        'No parameters': 'Sin parámetros en la URL (si hay formulario, llénalo abajo; si no, solo pulsa Ejecutar)', 'Edit Value': 'Editar', 'Schema': 'Estructura',\n        'Example Value': 'Ejemplo', 'Execute': '② ▶ Ejecutar', 'Clear': 'Limpiar', 'Responses': 'Resultado',\n        'Server response': '③ Respuesta del servidor (aquí ves el resultado)', 'Code': 'Código', 'Details': 'Detalle',\n        'Description': 'Descripción', 'Response body': 'Cuerpo de la respuesta', 'Response headers': 'Encabezados',\n        'Request duration': 'Duración', 'Request URL': 'URL consultada', 'Media type': 'Tipo', 'Name': 'Nombre',\n        'Controls Accept header.': '', 'required': 'obligatorio', 'Authorize': 'Autorizar (elegir rol)', 'Download': 'Descargar',\n        'Try it out': 'Probar', 'Available authorizations': 'Rol con el que se prueba', 'Close': 'Cerrar', 'Logout': 'Quitar rol'\n    };\n    const _traducir = (raiz) => {\n        const it = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);\n        for (let n = it.nextNode(); n; n = it.nextNode()) {\n            const s = n.nodeValue.trim();\n            if (s in _ES && n.nodeValue !== n.nodeValue.replace(s, _ES[s])) n.nodeValue = n.nodeValue.replace(s, _ES[s]);\n        }\n    };\n    new MutationObserver(() => _traducir(document.body)).observe(document.body, {childList: true, subtree: true, characterData: false});\n    _traducir(document.body);\n"

_FORMULARIO = '\n    // ---- Formulario: un cuadro por dato, generado desde el esquema real de la API ----\n    const _ETQ = {\n        nombre: \'Nombre\', identificacion_oficial: \'Identificación oficial (INE)\', telefono: \'Teléfono\', email: \'Correo electrónico\',\n        ciudad: \'Ciudad\', canal_preferido: \'Canal preferido\', tutor_id: \'ID del tutor\', especie: \'Especie\', raza: \'Raza\',\n        fecha_nacimiento: \'Fecha de nacimiento (AAAA-MM-DD)\', peso_kg: \'Peso (kg)\', microchip: \'Microchip\',\n        temperatura_c: \'Temperatura (°C)\', motivo: \'Motivo\', alergias: \'Alergias (separadas por coma)\', nivel: \'Nivel\',\n        principio_activo: \'Principio activo\', nuevo_tutor_id: \'ID del nuevo tutor\', descripcion_trauma: \'Descripción del trauma\',\n        paciente_id: \'ID de la mascota\', cedula_veterinario: \'Cédula del veterinario\', subjetivo: \'Subjetivo (S)\',\n        objetivo: \'Objetivo (O)\', analisis: \'Análisis (A)\', plan: \'Plan (P)\', cedula: \'Cédula profesional\', detalle: \'Detalle\',\n        dosis_mg_por_kg: \'Dosis (mg por kg)\', via: \'Vía de administración\', frecuencia_horas: \'Frecuencia (cada cuántas horas)\',\n        duracion_dias: \'Duración (días)\', justificacion: \'Justificación clínica\', cedula_justificante: \'Cédula de quien justifica\',\n        tipo_estudio: \'Tipo de estudio\', nombre_archivo: \'Nombre del archivo\', sha256: \'SHA-256 del archivo\',\n        nombre_vacuna: \'Nombre de la vacuna\', lote: \'Lote\', marca: \'Marca\', fecha_aplicacion: \'Fecha de aplicación (AAAA-MM-DD)\',\n        esquema: \'Esquema\', tipo: \'Tipo\', inicio: \'Fecha y hora de inicio\', duracion_min: \'Duración (minutos)\',\n        jaula_id: \'ID de la jaula\', plan_fluidoterapia: \'Plan de fluidoterapia\', contagioso: \'¿Es contagioso?\', critico: \'¿Es crítico?\',\n        frecuencia_cardiaca: \'Frecuencia cardiaca (lpm)\', frecuencia_respiratoria: \'Frecuencia respiratoria (rpm)\',\n        registrada_por: \'Registrada por\', monto: \'Monto ($)\', descripcion: \'Descripción\', lineas: \'Líneas de la orden (JSON)\',\n        promocion_activa: \'¿Promoción activa?\', autorizado: \'¿Autorizado?\', referencia: \'Referencia\', accion: \'Acción\'\n    };\n    const _setTexto = (ta, v) => {\n        Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, \'value\').set.call(ta, v);\n        ta.dispatchEvent(new Event(\'input\', {bubbles: true}));\n    };\n    const _ref = (spec, s) => { while (s && s.$ref) s = s.$ref.replace(\'#/\', \'\').split(\'/\').reduce((a, k) => a && a[k], spec); return s || {}; };\n    const _base = (spec, s) => {\n        s = _ref(spec, s);\n        if (!s.anyOf) return s;\n        const alt = s.anyOf.map(x => _ref(spec, x)).filter(x => x.type !== \'null\');\n        return alt.find(x => x.enum) || alt.find(x => x.type === \'string\') || alt[0] || {};\n    };\n    const _tipoCampo = f => f.enum ? \'enum\' : f.type === \'boolean\' ? \'bool\' : f.type === \'integer\' ? \'int\' : f.type === \'number\' ? \'num\'\n        : f.type === \'array\' ? ((f.items && f.items.type === \'string\') ? \'lista\' : \'json\') : f.format === \'date-time\' ? \'fecha\' : \'texto\';\n    const _formularios = () => {\n        let spec = null;\n        document.querySelectorAll(\'.swagger-ui .opblock.is-open\').forEach(op => {\n            const cuerpo = op.querySelector(\'.opblock-body\');\n            const ta = op.querySelector(\'textarea.body-param__text\');\n            const seccion = op.querySelector(\'.opblock-section-request-body\');\n            if (!cuerpo || !ta || !seccion || op.querySelector(\'.form-vc\') || !ta.value.trim()) return;\n            try {\n                spec = spec || ui.getSystem().specSelectors.specJson().toJS();\n                const ruta = (op.querySelector(\'.opblock-summary-path\') || {}).dataset.path;\n                const metodo = (op.className.match(/opblock-(get|post|put|patch|delete)/) || [])[1];\n                const rb = spec.paths[ruta][metodo].requestBody;\n                const esquema = _ref(spec, rb.content[\'application/json\'].schema);\n                const ej = JSON.parse(ta.value);\n                const req = esquema.required || [];\n                const campos = [];\n                const caja = document.createElement(\'div\');\n                caja.className = \'form-vc\';\n                caja.innerHTML = \'<div class="form-vc-titulo">✏️ Llena el formulario <span>(un cuadro por dato; los que dicen «opcional» puedes dejarlos vacíos)</span></div><div class="form-vc-grid"></div>\'\n                    + \'<button type="button" class="form-vc-json">Ver / editar como JSON (avanzado)</button>\';\n                const grid = caja.querySelector(\'.form-vc-grid\');\n                Object.entries(esquema.properties || {}).forEach(([nombre, def]) => {\n                    const f = _base(spec, def), k = _tipoCampo(f), v = ej[nombre], esReq = req.includes(nombre);\n                    const lab = document.createElement(\'label\');\n                    lab.className = \'form-vc-campo\' + (k === \'json\' ? \' ancho\' : \'\');\n                    const t = document.createElement(\'span\');\n                    t.innerHTML = (_ETQ[nombre] || nombre.replace(/_/g, \' \')) + (esReq ? \' <b>*</b>\' : \' <i>opcional</i>\');\n                    let el;\n                    if (k === \'enum\') {\n                        el = document.createElement(\'select\');\n                        if (!esReq) el.add(new Option(\'— (vacío)\', \'\'));\n                        f.enum.forEach(o => el.add(new Option(o, o)));\n                        el.value = v == null ? (esReq ? f.enum[0] : \'\') : v;\n                    } else if (k === \'bool\') {\n                        el = document.createElement(\'input\'); el.type = \'checkbox\'; el.checked = !!v;\n                        lab.classList.add(\'check\');\n                    } else if (k === \'json\') {\n                        el = document.createElement(\'textarea\'); el.rows = 7;\n                        el.value = v == null ? \'\' : JSON.stringify(v, null, 2);\n                    } else {\n                        el = document.createElement(\'input\');\n                        el.type = k === \'int\' || k === \'num\' ? \'number\' : k === \'fecha\' ? \'datetime-local\' : \'text\';\n                        if (k === \'num\') el.step = \'any\';\n                        el.value = v == null ? \'\' : k === \'fecha\' ? String(v).slice(0, 16) : k === \'lista\' ? [].concat(v).join(\', \') : v;\n                    }\n                    lab.append(t, el);\n                    if (f.description) { const h = document.createElement(\'small\'); h.textContent = f.description; lab.append(h); }\n                    grid.append(lab);\n                    campos.push({nombre, k, el, req: esReq});\n                });\n                const leer = () => {\n                    const o = {};\n                    campos.forEach(c => {\n                        let x;\n                        if (c.k === \'bool\') x = c.el.checked;\n                        else {\n                            const raw = c.el.value.trim();\n                            if (raw === \'\') { if (!c.req) return; x = (c.k === \'int\' || c.k === \'num\') ? null : \'\'; }\n                            else if (c.k === \'int\') x = parseInt(raw, 10);\n                            else if (c.k === \'num\') x = Number(raw);\n                            else if (c.k === \'lista\') x = raw.split(\',\').map(s => s.trim()).filter(Boolean);\n                            else if (c.k === \'json\') { try { x = JSON.parse(raw); } catch (e) { x = raw; } }\n                            else if (c.k === \'fecha\') x = raw.length === 16 ? raw + \':00\' : raw;\n                            else x = raw;\n                        }\n                        o[c.nombre] = x;\n                    });\n                    return o;\n                };\n                caja.addEventListener(\'input\', () => _setTexto(ta, JSON.stringify(leer(), null, 2)));\n                caja.addEventListener(\'change\', () => _setTexto(ta, JSON.stringify(leer(), null, 2)));\n                caja.querySelector(\'.form-vc-json\').addEventListener(\'click\', () => caja.classList.toggle(\'json-on\'));\n                seccion.parentNode.insertBefore(caja, seccion);\n                _setTexto(ta, JSON.stringify(leer(), null, 2));\n            } catch (e) { console.warn(\'formulario:\', e.message); }\n        });\n    };\n    let _pend = false;\n    new MutationObserver(() => { if (_pend) return; _pend = true; requestAnimationFrame(() => { _pend = false; _formularios(); }); })\n        .observe(document.body, {childList: true, subtree: true});\n    setInterval(_formularios, 400);\n    </script>'


def pagina_docs(openapi_url: str, titulo: str, js_url: str | None = None, css_url: str | None = None,
                rol: str = ROL_POR_OMISION_EN_DOCS) -> HTMLResponse:
    """Swagger UI con opciones más cómodas y el rol DIRECTOR ya autorizado (se puede cambiar en Authorize)."""
    extra: dict[str, Any] = {}
    if js_url:
        extra["swagger_js_url"] = js_url
    if css_url:
        extra["swagger_css_url"] = css_url
    html = get_swagger_ui_html(
        openapi_url=openapi_url, title=titulo, swagger_favicon_url="data:,",
        swagger_ui_parameters={"persistAuthorization": True, "displayRequestDuration": True, "docExpansion": "list",
                               "defaultModelsExpandDepth": -1, "tryItOutEnabled": True, "filter": True,
                               "tagsSorter": "alpha"},
        **extra).body.decode()
    # Vista limpia: los errores 400/404/409/422 ya están explicados arriba (guía) y en cada «Server response» real;
    # se ocultan de la tabla estática de cada recurso, pero siguen completos en /openapi.json.
    estilo = ("<style>"
              ".swagger-ui .responses-table:not(.live-responses-table) tr.response[data-code='400'],"
              ".swagger-ui .responses-table:not(.live-responses-table) tr.response[data-code='404'],"
              ".swagger-ui .responses-table:not(.live-responses-table) tr.response[data-code='409'],"
              ".swagger-ui .responses-table:not(.live-responses-table) tr.response[data-code='422']{display:none}"
              ".swagger-ui .response-col_links{display:none}"
              ".swagger-ui .opblock-description-wrapper p,.swagger-ui .opblock-description-wrapper li{font-size:14px;line-height:1.5}"
              ".swagger-ui .info .title small{display:none}"
              # Dónde se escribe: lo editable va marcado en azul y cada operación abierta trae su mini-guía.
              ".swagger-ui .btn.try-out__btn{display:none}"
              ".swagger-ui .opblock-body textarea.body-param__text{border:3px solid #2f80ed;background:#f4f9ff}"
              ".swagger-ui .opblock-body .parameters-col_description input[type=text]{border:3px solid #2f80ed;background:#f4f9ff}"
              ".swagger-ui .opblock.is-open .opblock-body::before{display:block;white-space:pre-line;margin:0;padding:14px 20px;"
              "background:#fffbe6;border-bottom:1px solid #f0d98a;color:#4a3b00;font-size:14px;line-height:1.6;"
              "content:'CÓMO USARLO\\A ①  Llena los cuadros AZULES (el formulario y/o los Parámetros).\\A "
              "②  Pulsa el botón ▶ Ejecutar.\\A ③  El resultado aparece más abajo, en «Respuesta del servidor».'}"
              ".swagger-ui .response-control-media-type__accept-message{display:none}"
              ".swagger-ui .form-vc{margin:0;padding:16px 20px;background:#fff;border-bottom:1px solid #d9ddd8}"
              ".swagger-ui .form-vc-titulo{font-size:16px;font-weight:700;margin-bottom:12px}"
              ".swagger-ui .form-vc-titulo span{font-weight:400;font-size:13px;color:#5b6770}"
              ".swagger-ui .form-vc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px 20px}"
              ".swagger-ui .form-vc-campo{display:flex;flex-direction:column;gap:5px;font-size:13px;font-weight:600;margin:0}"
              ".swagger-ui .form-vc-campo.ancho{grid-column:1/-1}"
              ".swagger-ui .form-vc-campo b{color:#d93025}.swagger-ui .form-vc-campo i{font-weight:400;color:#8a949b;font-size:12px}"
              ".swagger-ui .form-vc-campo small{font-weight:400;color:#5b6770}"
              ".swagger-ui .form-vc-campo input[type=text],.swagger-ui .form-vc-campo input[type=number],"
              ".swagger-ui .form-vc-campo input[type=datetime-local],.swagger-ui .form-vc-campo select,.swagger-ui .form-vc-campo textarea"
              "{width:100%;box-sizing:border-box;margin:0;padding:9px 10px;font-size:15px;border:3px solid #2f80ed;border-radius:6px;background:#f4f9ff;font-weight:400}"
              ".swagger-ui .form-vc-campo.check{flex-direction:row;align-items:center;gap:10px;font-size:15px}"
              ".swagger-ui .form-vc-campo.check input{width:22px;height:22px;margin:0}"
              ".swagger-ui .form-vc-json{margin-top:14px;background:none;border:0;color:#2f80ed;cursor:pointer;font-size:13px;text-decoration:underline;padding:0}"
              ".swagger-ui .form-vc ~ .opblock-section-request-body{display:none}"
              ".swagger-ui .form-vc.json-on ~ .opblock-section-request-body{display:block}"
              ".swagger-ui .execute-wrapper .btn.execute{font-size:16px;padding:12px}"
              "</style></head>")
    html = html.replace("</head>", estilo, 1)
    # El esquema de seguridad solo existe cuando Swagger terminó de cargar /openapi.json: se espera con un sondeo corto.
    # Si la persona ya eligió otro rol en «Authorize» (persistAuthorization), se respeta.
    precarga = (
        "\n    const _esperaRol = setInterval(() => { try {"
        "\n        const sys = ui.getSystem();"
        "\n        const defs = sys.specSelectors.securityDefinitions();"
        "\n        if (!defs || !defs.size) return;"
        "\n        clearInterval(_esperaRol);"
        f"\n        if (!sys.authSelectors.authorized().size) ui.preauthorizeApiKey('X-Rol', '{rol}');"
        "\n    } catch (e) { /* aún cargando */ } }, 150);"
        "\n    setTimeout(() => clearInterval(_esperaRol), 15000);"
        + _TRADUCCION + _FORMULARIO)
    marcador = "    })\n    </script>"
    if marcador not in html:  # versión distinta de FastAPI: se deja la página estándar, sin precarga
        return HTMLResponse(html)
    return HTMLResponse(html.replace(marcador, "    })" + precarga, 1))
