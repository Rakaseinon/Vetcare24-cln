# VetCare 24 — Sistema de gestión clínica y hospitalaria 24/7

PIA · *Componentes de Lógica de Negocio* · FIME-UANL · **Equipo 4** — Giovani Aldahir Patiño Rodríguez (2118917), Leonardo Alonso Muñiz Espinosa (2115635), Aldo René Romero Parga (2118748).
Profesor: Miguel Ángel Gómez Marroquín · Caso 04: VetCare 24.

| | |
|---|---|
| **Repositorio** | https://github.com/Rakaseinon/Vetcare24-cln |
| **API desplegada (Swagger UI)** | https://vetcare24-api-dwsa.onrender.com/docs |
| **Contrato OpenAPI** | [`docs/api/openapi.json`](docs/api/openapi.json) (38 rutas) |

## ¿Qué es?
API REST con **Domain Model (DDD)** para una clínica veterinaria 24/7: identidad tutor–mascota, agenda por servicio, urgencias (Código Rojo),
expediente clínico con **notas inmutables y enmiendas**, **bloqueo por alergia**, vacunación con refuerzos y recordatorios, hospitalización con
**alta cruzada** y reportes. Implementa las **15 historias de usuario** y las reglas **RN-01…RN-06** del BRD del equipo, y resuelve el paquete de datos
(40 tutores, 20 servicios, 60 órdenes, 120 casos y 20 transiciones) con **Specification** (AND/OR/NOT), **State Machine** y **Domain Events**.

## Arranque rápido
Requisitos: Python 3.12+ (o Docker).

```bash
python -m venv .venv && source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export SEED_ON_START=true                                    # variables de entorno: ver tabla «Configuración»
uvicorn src.api.main:create_app --factory --reload
# → http://localhost:8000/docs   (Swagger UI)    http://localhost:8000/health
```

**Con Docker Compose** (PostgreSQL + API + pruebas):
```bash
cp .env.example .env                 # Compose lee .env (credenciales de PostgreSQL); cámbialas
docker compose up --build            # API en http://localhost:8000/docs  (BD PostgreSQL en el servicio db)
docker compose run --rm tests        # suite completa con cobertura mínima 80 %
```

### Interfaz visual (`/app`)
Además del Swagger hay una **interfaz web aparte** en `/app` (local: http://localhost:8000/app; producción: `https://vetcare24-api-dwsa.onrender.com/app`). Es una sola página HTML/JS sin dependencias (`src/api/static/app.html`) que consume esta misma API, así que respeta las mismas reglas de negocio y los mismos permisos por rol.

- **Rol** en la barra superior (cabecera `X-Rol`): cambia a RECEPCION, VETERINARIO, ENFERMERIA o DIRECTOR para ver el 403 de RNF-03.
- **Pantallas:** Inicio (KPIs), Tutores y mascotas, Consultas y urgencias, Vacunas y citas, Hospitalización (mapa de jaulas) y Órdenes de servicio.
- **IDs encadenados:** el tutor, la mascota, la consulta, etc. que creas quedan arriba y se llenan solos en los siguientes formularios.
- **Demostración automática** (Inicio → «Ejecutar demostración»): corre los 18 pasos del flujo completo (RN-01, RN-03, RN-04, RN-06) y marca si cada uno respondió lo esperado.

### Probar en Swagger
`/docs` (y también la raíz `/`) abre Swagger UI **en español**, con los recursos agrupados por pasos, una guía de recorrido arriba y un ejemplo válido ya escrito en cada cuerpo.

1. **Rol:** la página entra sola como `DIRECTOR` (puede usar todo). Para cambiarlo pulsa **Authorize** → `X-Rol` → `RECEPCION`, `VETERINARIO`, `ENFERMERIA` o `DIRECTOR`. Sin rol, la API responde 401.
2. **Probar:** abre un recurso → **Try it out** → **Execute**. La respuesta real está en **Server response**, debajo del recuadro oscuro del `curl`; el ejemplo gris de más abajo es solo documentación.
3. **Datos del profesor:** con `SEED_ON_START=true` ya existen `VET-C012` (tutor), `VET-P001…` (servicios) y `VET-O001…` (órdenes); p. ej. `GET /ordenes/VET-O001` → total `7587.00`, `puede_procesarse: true`.
4. **Recorrido de demo** (cada paso usa el `id` del anterior): `POST /tutores` → `POST /pacientes` → `POST /pacientes/{id}/alergias` (penicilina) → `POST /consultas` → `POST …/recetas` (**409 bloqueo RN-04**) → mismo POST con `justificacion` + `cedula_justificante` (201) → `PUT …/nota` → `POST …/nota/firmar` → `PUT …/nota` (**409 RN-01**) → `POST …/enmiendas` (201) → `POST /hospitalizaciones` (jaula `JP-01`) → `…/alta-medica` (pendiente) → `…/liquidacion` (**egreso concluido, jaula libre**).
5. **Control de acceso (RNF-03):** cambia el rol a `RECEPCION` y pide `GET /pacientes/{id}/expediente` → **403**.

Cédula profesional de prueba: cualquier número de 7–8 dígitos (p. ej. `1234567`).

## Pruebas y cobertura
```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
TEST_DATABASE_URL=postgresql://usuario:clave@localhost:5432/pruebas pytest     # mismas pruebas sobre PostgreSQL real
```
| Medición (última ejecución) | Resultado |
|---|---|
| Pruebas | **343 pasan** (SQLite en memoria **y** PostgreSQL 16) |
| Cobertura total | **99.0 %** (exigido ≥ 80 %) |
| Por capa | dominio **100 %** · API 99.0 % · infraestructura 99.0 % · aplicación 96.3 % |
| Oráculo independiente | 120 casos + 20 transiciones del paquete, recalculados solo con `csv`+`Decimal` y comparados contra la API |

Las pruebas están en `tests/unit` (dominio puro, sin BD) y `tests/integration` (API + persistencia). CI (`.github/workflows/ci.yml`) las corre contra un PostgreSQL de servicio.

## Estructura
```
src/domain/          Agregados, Value Objects, Specifications, State Machines, eventos, servicios de dominio  (sin dependencias técnicas)
src/application/     Servicios de aplicación (orquestan: cargar → dominio → guardar → commit), puertos, vistas
src/infrastructure/  Repositorios SQLAlchemy, UnitOfWork, codec JSON/JSONB, bus de eventos, notificador, semilla, config 12-Factor
src/api/             FastAPI: rutas, esquemas Pydantic, RBAC, manejo de errores
tests/               unit/ e integration/
docs/                BRD.md · COMO_CORRER.md · TRAZABILIDAD.md · DIFERENCIAS_PAQUETE_DATOS.md · GLOSARIO.md · architecture/ (UML de clases, SOLID.md, ADR-001…006) · api/openapi.json · analisis/originales/ (PDFs U2/U3)
scripts/             ejecutar_casos_prueba.py · exportar_openapi.py · generar_trazabilidad.py
data/                paquete de datos ficticio (CSV) + resultados/
```

## Configuración (12-Factor)
| Variable | Por omisión | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./vetcare24.db` | SQLite local o PostgreSQL (`postgres://` y `postgresql://` se normalizan a `postgresql+psycopg2://`) |
| `SEED_ON_START` | `false` | `true` carga jaulas y el paquete de datos al iniciar (idempotente) |
| `DATA_DIR` | `./data` | Carpeta de los CSV |
| `ENVIRONMENT` | `development` | Etiqueta que devuelve `/health` |
| `PORT` | `8000` | Puerto (lo inyectan Render/Railway/Fly.io) |

## Reglas de negocio → dónde viven
| Regla | Dominio | Endpoint de demo |
|---|---|---|
| RN-01 nota inmutable + enmiendas | `Consulta.firmar_y_cerrar`, `anexar_enmienda` | `PUT /consultas/{id}/nota` → 409 tras firmar |
| RN-02 Código Rojo | `Consulta.admitir_urgencia` | `POST /urgencias` |
| RN-03 lote y marca obligatorios | `RegistroVacuna.aplicar` | `POST /vacunas` → 400 sin lote |
| RN-04 bloqueo por alergia (ADR-002) | `ServicioValidacionAlergias` | `POST /consultas/{id}/recetas` → 409 |
| RN-05 transferencia conserva historial | `Paciente.transferir_a` | `POST /pacientes/{id}/transferencia` |
| RN-06 alta cruzada | `ServicioAltaHospitalaria` + `MAQUINA_HOSPITALIZACION` | `…/alta-medica` + `…/liquidacion` |

Trazabilidad completa y verificada automáticamente: [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md).

## Despliegue (Render, gratuito)
1. Sube el repo a GitHub. 2. En Render: **New → Blueprint** → selecciona el repo (usa [`render.yaml`](render.yaml): PostgreSQL + servicio web Docker).
3. Espera el build y abre `https://<servicio>.onrender.com/docs`. 4. (Opcional) crea un *Deploy Hook* y guárdalo como secreto `RENDER_DEPLOY_HOOK` en GitHub para despliegue automático desde CI.
Railway/Fly.io: mismo `Dockerfile` (`--target app`), define `DATABASE_URL` y `SEED_ON_START=true`.

## Limitaciones conocidas
Autenticación por encabezado `X-Rol` solo demostrativa (ADR-004) · notificaciones simuladas (`LogNotificador`) · archivos de laboratorio: solo metadato + SHA-256 ·
rangos de signos vitales de referencia sin validación clínica · consentimiento informado y lista de espera fuera de alcance.
Detalle y justificación en [`docs/DIFERENCIAS_PAQUETE_DATOS.md`](docs/DIFERENCIAS_PAQUETE_DATOS.md).
