# Guía de estudio para la defensa

Objetivo: que cada integrante pueda **explicar con sus palabras** qué hace el código y por qué se diseñó así. Léela con el código abierto, en este orden.

## 1. El proyecto en 60 segundos
> «VetCare 24 es una API REST en Python/FastAPI con arquitectura limpia. Las reglas del negocio (RN-01…RN-06) viven en el **dominio** como objetos ricos
> que se protegen solos; la capa de **aplicación** solo orquesta; la **infraestructura** guarda en PostgreSQL/SQLite; la **API** expone el contrato OpenAPI.
> Usamos Specification para las reglas combinables, State Machine para los ciclos de vida y Domain Events para avisar lo que pasó.
> Se prueba con 343 pruebas (99 % de cobertura) contra SQLite y PostgreSQL, y con un oráculo independiente para el paquete de datos.»

## 2. Orden de lectura del código (≈ 90 min)
| # | Archivo | Qué entender | Pregunta que te pueden hacer |
|---|---|---|---|
| 1 | `src/domain/common.py` | `Specification` (`&`, `|`, `~`, `reasons()`), `StateMachine` (tabla estado×acción), `AggregateRoot` (`_record`/`pull_events`), jerarquía de errores | ¿Por qué `reasons()`? → para responder *qué* regla falló, no solo «inválido» |
| 2 | `src/domain/specifications.py` | cómo se arma `puede_procesarse = TutorActivo & OrdenConLineas & OrdenAutorizada` y `beneficio = Preferente & TotalMinimo & ~Promoción` | ¿Dónde está el NOT? → `~PromocionActivaSpec()` |
| 3 | `src/domain/orden_servicio.py` | `MAQUINA_ORDEN`, `aprobar` valida la transición **y luego** la Specification | ¿Qué pasa al aprobar dos veces? → `InvalidStateTransition` → 409 |
| 4 | `src/domain/paciente.py` | Value Objects inmutables (`Peso`, `Alergeno`, `MicrochipCode`), `registrar_alergia`, `transferir_a` (RN-05) | ¿Por qué `Peso` es un VO y no un número? → inmutable, validado, sin identidad |
| 5 | `src/domain/consulta.py` | RN-01: `_asegurar_editable()` + `firmar_y_cerrar` + `anexar_enmienda`; US14 laboratorio | ¿Cómo garantizan que nadie edite una nota firmada? → no hay camino de código: toda mutación pasa por `_asegurar_editable` |
| 6 | `src/domain/servicios.py` | `ServicioValidacionAlergias` (RN-04 + excepción ADR-002), `ServicioAltaHospitalaria` (RN-06) | ¿Por qué servicio de dominio y no método de Consulta? → involucra **dos** agregados (Paciente y Consulta) |
| 7 | `src/domain/hospitalizacion.py` | `ConstantesVitales.alertas`, ventana 4 h/2 h, `firmar_alta_medica`/`liquidar_cuenta`/`intentar_egreso` | ¿Cuándo se libera la jaula? → solo con alta firmada **y** cuenta liquidada |
| 8 | `src/domain/profilaxis.py`, `agenda.py` | cálculo de refuerzo; duración por servicio, sala sin solape | ¿Cómo evitan el sobrecupo? → `SalaLibreSpec` sobre las citas activas del lapso |
| 9 | `src/infrastructure/uow.py` + `repositories.py` + `codec.py` | transacción atómica; eventos **después** del commit; un agregado = una fila (ADR-003) | ¿Por qué JSON en la BD? → el dominio no conoce el ORM y se guarda el agregado completo |
| 10 | `src/application/services.py` | patrón: `with uow: cargar → dominio → guardar → commit` | ¿Hay lógica de negocio aquí? → no; solo unicidad que requiere repositorio |
| 11 | `src/api/routes.py`, `security.py`, `main.py` | controladores delgados; RBAC por rol; mapeo de errores 400/404/409/422 | ¿Cómo manejan errores? → *exception handlers* por tipo de excepción de dominio |
| 12 | `tests/` | pirámide: unit (dominio) → integration (API); oráculo | ¿Cómo saben que el dominio es correcto sin comparar contra sí mismo? → el oráculo recalcula desde el CSV |

## 3. Recorrido de una petición: `POST /consultas/{id}/recetas` (RN-04)
1. `routes.prescribir` valida el JSON (Pydantic) y el rol (`requiere(VETERINARIO, DIRECTOR)`), y llama a `ConsultaService.prescribir`.
2. El servicio abre el `UnitOfWork`, carga `Consulta` y `Paciente`, y construye el `MedicamentoDosificado` (dosis por kg × peso).
3. Llama a `ServicioValidacionAlergias.prescribir`: si el principio activo ∈ alergias del paciente y no hay justificación → `AlergiaBloqueoError`.
4. El servicio hace `rollback()`, publica `BloqueoAlergiaDisparadoEvent` (auditoría) y relanza; el *handler* responde **409**.
5. Si no hay conflicto (o hay justificación con cédula): se agrega a la receta, `save`, `commit`, y **recién entonces** se publican los eventos.

## 4. Preguntas probables y respuestas cortas
- **¿Por qué DDD y no Transaction Script?** ADR-001: las reglas son entrelazadas y con estado; en DDD el agregado las hace cumplir y se prueban sin BD.
- **¿Qué es un agregado y cuáles tienen?** Unidad de consistencia con una raíz. Paciente, Consulta, Hospitalización, Profilaxis (ADR-001) + Cita, OrdenServicio, Tutor. Se referencian por id.
- **¿Qué diferencia hay entre Specification y un `if`?** Es un objeto reutilizable y componible (`&`, `|`, `~`) que además explica por qué falla (`reasons`).
- **¿Dónde está la máquina de estados?** `MAQUINA_*` en `orden_servicio.py`, `hospitalizacion.py`, `agenda.py`; clase `StateMachine` en `common.py`.
- **¿Cómo garantizan la atomicidad?** `SqlAlchemyUnitOfWork`: una transacción por caso de uso; rollback ante excepción; eventos solo post-commit.
- **¿Cómo prueban con PostgreSQL?** `TEST_DATABASE_URL` hace que las mismas pruebas corran contra PostgreSQL (CI lo levanta como servicio). Así detectamos que `postgresql://` usaba el driver equivocado (ver `normalizar_url`).
- **¿Dónde aplican SOLID?** `docs/architecture/SOLID.md`, con código real de cada principio. Lo más fácil de demostrar es **D**: `tests/unit/test_arquitectura.py` analiza los `import` y falla si `domain` depende de `application`, `infrastructure` o `api`. Para **O**: agregar una regla es una `Specification` nueva y un estado nuevo es una fila de la tabla.
- **¿Por qué los ADR tienen alternativas?** Porque una decisión sin alternativas descartadas no es una decisión: cada ADR (001–006) trae contexto, decisión, alternativas y consecuencias.
- **¿Qué NO hicieron?** Autenticación real (solo `X-Rol`), mensajería real, almacenamiento de archivos, consentimiento informado, lista de espera, UI. Está documentado en `DIFERENCIAS_PAQUETE_DATOS.md`.
- **¿Qué supuestos clínicos hicieron?** Rangos de signos vitales y esquema por edad (< 12 meses → 21 días): son supuestos a validar con el Director Médico.
- **¿Cómo evitan que la matriz de trazabilidad mienta?** `tests/unit/test_trazabilidad.py` verifica que cada archivo/símbolo/prueba citado exista y que el `.md` esté generado.

## 5. Guion de demo (5 min, en Swagger desplegado)
1. `GET /health` y abrir `/docs` (OpenAPI). Entra solo como `DIRECTOR`; para mostrar RBAC usa **Authorize** y cambia el rol cuando haga falta.
2. **Dataset:** `GET /ordenes/VET-O001` (total 7 587.00) → `POST …/transiciones` `completar` → **409** (salto de estado) → `aprobar` → 200.
3. **RN-04:** crear tutor y mascota → alergia «penicilina» → consulta → receta penicilina → **409** → con justificación → 201.
4. **RN-01:** firmar la nota → `PUT nota` → **409** → enmienda → 201 (la nota original queda intacta).
5. **RN-06:** hospitalizar → `alta-medica` (pendiente) → `liquidacion` (con `RECEPCION` o `DIRECTOR`) → *EGRESO_CONCLUIDO* y `GET /jaulas?libres=true`.
6. **RNF-03:** Authorize con `RECEPCION` → `GET /pacientes/{id}/expediente` → **403**.
7. Cerrar mostrando el reporte de cobertura (`pytest --cov`) y `docs/TRAZABILIDAD.md`.

## 6. Plan de Git (para que el historial sea real y de los tres)
El PIA pide historial de commits del equipo. **Cada integrante debe hacer sus propios commits desde su cuenta** (no se simula autoría). Propuesta de reparto:

| Integrante | Área sugerida | Ramas / PRs ejemplo |
|---|---|---|
| Giovani | Dominio clínico (Consulta, Paciente) y API | `feat/dominio-consulta`, `feat/api-expediente` |
| Aldo | Hospitalización, Profilaxis, Agenda | `feat/hospitalizacion-rn06`, `feat/profilaxis`, `feat/agenda` |
| Leonardo | Infraestructura, pruebas, CI/CD, Docker, despliegue | `feat/persistencia`, `test/oraculo-dataset`, `ci/github-actions`, `chore/docker` |

Flujo: `main` protegida → cada área en su rama → *pull request* revisado por otro integrante → merge. Commits pequeños y descriptivos
(`feat(dominio): bloquear receta por alergia (RN-04)`, `test: oráculo del paquete de datos`). Antes de entregar, que cada quien **lea y pueda explicar** el módulo que firma.
