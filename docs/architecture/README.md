# Arquitectura de VetCare 24

Arquitectura limpia con **Domain Model (DDD)** — decisión formal en [ADR-001](adr/ADR-001-domain-model-ddd.md).
La regla de dependencia apunta siempre hacia el dominio: `api → application → domain ← infrastructure`.

```mermaid
flowchart LR
    subgraph API["src/api  (FastAPI)"]
        R[routes.py<br/>controladores delgados]
        SEC[security.py<br/>RBAC X-Rol]
        SCH[schemas.py<br/>contrato OpenAPI]
    end
    subgraph APP["src/application"]
        SVC[Servicios de aplicación<br/>cargar → invocar dominio → guardar → commit]
        PORTS[ports.py<br/>UnitOfWork · EventBus · Notificador]
    end
    subgraph DOM["src/domain  (sin dependencias técnicas)"]
        AGG[Agregados · Value Objects]
        SPEC[Specifications · State Machines]
        DS[Servicios de dominio]
        EV[Eventos de dominio]
    end
    subgraph INF["src/infrastructure"]
        REPO[Repositorios SQLAlchemy]
        UOW[UnitOfWork]
        BUS[InMemoryEventBus]
        NOT[LogNotificador]
    end
    DB[(SQLite / PostgreSQL)]
    R --> SVC --> AGG
    SVC --> PORTS
    UOW -.implementa.-> PORTS
    BUS -.implementa.-> PORTS
    NOT -.implementa.-> PORTS
    REPO --> DB
    UOW --> REPO
    REPO --> AGG
```

## Agregados (ADR-001 + extensiones)

| Agregado (raíz) | Módulo | Invariantes principales |
|---|---|---|
| `Paciente` (+ `TutorResponsable`, `HojaTriaje`) | `paciente.py` | microchip único; alergias sin duplicar; transferencia conserva historial (RN-05) |
| `Consulta` (+ `NotaSOAP`, `NotaEnmienda`, `ItemReceta`, `EstudioLaboratorio`) | `consulta.py` | nota firmada = congelada (RN-01); urgencia sin trámites (RN-02); resultados de laboratorio se anexan sin editar la nota |
| `Hospitalizacion` (+ bitácora, precuenta) y `Jaula` | `hospitalizacion.py` | lecturas cada 4 h / 2 h crítico; alta cruzada (RN-06) |
| `RegistroVacuna` (+ `ProgramacionRefuerzo`) | `profilaxis.py` | lote y marca obligatorios (RN-03); refuerzo 21/28/365 días |
| `Cita` | `agenda.py` | duración por servicio, sala compatible sin solapes, cancelación tardía < 4 h |
| `OrdenServicio` | `orden_servicio.py` | `puede_procesarse`, beneficio de referencia, máquina de estados (paquete de datos) |
| `Tutor` | `tutor.py` | contacto válido; tutor inactivo no asume responsabilidades |

Los agregados se referencian **solo por id** (`paciente_id`, `tutor_id`): cada transacción modifica un único agregado.

## Diagramas de clases del dominio (UML)

Cada diagrama muestra un agregado con sus entidades internas y Value Objects (rombo lleno = composición dentro del agregado; rombo vacío = opcional).
Todas las raíces `<<aggregate root>>` heredan de `AggregateRoot` (`src/domain/common.py`), que registra los eventos de dominio (`_record`, `pull_events`).
Las flechas punteadas son referencias **por id** entre agregados: ninguno guarda al otro, y cada transacción modifica uno solo.

**1 · Tutor y Paciente**

```mermaid
classDiagram
    direction TB
    class Tutor { <<aggregate root>>
        +registrar()
        +asegurar_activo()
    }
    class Paciente { <<aggregate root>>
        +registrar()
        +registrar_triaje()
        +registrar_alergia()
        +alerta_alergia()
        +transferir_a() RN-05
    }
    class MicrochipCode { <<value object>> }
    class Peso { <<value object>> }
    class Alergeno { <<value object>> }
    class HojaTriaje { <<value object>> }
    class TutorResponsable { <<value object>> }
    Paciente *-- MicrochipCode
    Paciente *-- Peso
    Paciente *-- Alergeno
    Paciente *-- HojaTriaje
    Paciente *-- TutorResponsable
    Paciente ..> Tutor : tutor_id
```

**2 · Consulta (nota SOAP, receta, enmiendas y laboratorio)**

```mermaid
classDiagram
    direction TB
    class Consulta { <<aggregate root>>
        +abrir()
        +admitir_urgencia() RN-02
        +redactar_soap()
        +firmar_y_cerrar() RN-01
        +anexar_enmienda()
        +agregar_a_receta()
        +solicitar_estudio()
        +adjuntar_resultado()
    }
    class CedulaProfesional { <<value object>> }
    class NotaSOAP
    class NotaEnmienda { <<value object>> }
    class ItemReceta { <<value object>> }
    class MedicamentoDosificado { <<value object>> }
    class JustificacionClinica { <<value object>> }
    class EstudioLaboratorio
    class ResultadoLaboratorio { <<value object>> }
    Consulta *-- CedulaProfesional
    Consulta *-- NotaSOAP
    Consulta *-- NotaEnmienda
    Consulta *-- ItemReceta
    ItemReceta *-- MedicamentoDosificado
    ItemReceta o-- JustificacionClinica
    Consulta *-- EstudioLaboratorio
    EstudioLaboratorio o-- ResultadoLaboratorio
    Consulta ..> Paciente : paciente_id
```

**3 · Hospitalización y Jaula**

```mermaid
classDiagram
    direction TB
    class Hospitalizacion { <<aggregate root>>
        +ingresar()
        +registrar_constantes()
        +firmar_alta_medica()
        +liquidar_cuenta()
        +intentar_egreso() RN-06
    }
    class Jaula { <<aggregate root>>
        +ocupar()
        +liberar()
    }
    class LecturaBitacora { <<value object>> }
    class ConstantesVitales { <<value object>> }
    class ConsumoPrecuenta { <<value object>> }
    Hospitalizacion *-- LecturaBitacora
    LecturaBitacora *-- ConstantesVitales
    Hospitalizacion *-- ConsumoPrecuenta
    Hospitalizacion ..> Paciente : paciente_id
    Hospitalizacion ..> Jaula : jaula_id
```

**4 · Vacunas, Citas y Órdenes de servicio**

```mermaid
classDiagram
    direction TB
    class RegistroVacuna { <<aggregate root>>
        +aplicar() RN-03
        +marcar_notificado()
    }
    class Cita { <<aggregate root>>
        +programar()
        +cancelar()
        +atender()
    }
    class OrdenServicio { <<aggregate root>>
        +solicitar()
        +aprobar()
        +completar()
        +cancelar()
        +puede_procesarse()
    }
    class ServicioCatalogo { <<aggregate root>> }
    class LoteBiologico { <<value object>> }
    class MarcaVacuna { <<value object>> }
    class ProgramacionRefuerzo
    class LineaOrden { <<value object>> }
    RegistroVacuna *-- LoteBiologico
    RegistroVacuna *-- MarcaVacuna
    RegistroVacuna *-- ProgramacionRefuerzo
    OrdenServicio *-- LineaOrden
    RegistroVacuna ..> Paciente : paciente_id
    Cita ..> Paciente : paciente_id
    OrdenServicio ..> Tutor : tutor_id
    LineaOrden ..> ServicioCatalogo : servicio_id
```

### Specification y State Machine sobre el modelo

**5 · Specification** (cada regla es una clase pequeña; los operadores las combinan)

```mermaid
classDiagram
    direction TB
    class Specification~T~ { <<abstract>>
        +is_satisfied_by(candidato) bool
        +reasons(candidato) list~str~
    }
    class AndSpecification
    class OrSpecification
    class NotSpecification
    class TutorActivoSpec
    class AlergenoCoincideSpec
    class SalaLibreSpec
    Specification <|-- AndSpecification
    Specification <|-- OrSpecification
    Specification <|-- NotSpecification
    Specification <|-- TutorActivoSpec
    Specification <|-- AlergenoCoincideSpec
    Specification <|-- SalaLibreSpec
```

Usos: `OrdenServicio.puede_procesarse` = `TutorActivo & OrdenConLineas & OrdenAutorizada`; `elegible_beneficio_referencia` = `TutorPreferente & TotalMinimo & ~PromocionActiva`;
`Hospitalizacion.es_apto_para_egreso` = `AltaMedicaFirmada & CuentaLiquidada`; `ServicioValidacionAlergias` usa `AlergenoCoincideSpec`; `ServicioAgenda` usa `SalaLibreSpec` e `InicioFuturoSpec`.

**6 · State Machine y servicios de dominio**

```mermaid
classDiagram
    direction LR
    class StateMachine~S~ {
        +fire(estado, accion) S
        +permitidas(estado) list
        +tabla() list
    }
    class OrdenServicio
    class Hospitalizacion
    class Cita
    class ServicioValidacionAlergias { +prescribir() RN-04 }
    class ServicioIngresoHospitalario { +ingresar() US09 }
    class ServicioAltaHospitalaria { +procesar() RN-06 }
    class ServicioAgenda { +agendar() US02 }
    OrdenServicio ..> StateMachine : MAQUINA_ORDEN
    Hospitalizacion ..> StateMachine : MAQUINA_HOSPITALIZACION
    Cita ..> StateMachine : MAQUINA_CITA
    ServicioAltaHospitalaria ..> Hospitalizacion : orquesta
    ServicioIngresoHospitalario ..> Hospitalizacion : crea
    ServicioAgenda ..> Cita : crea
```

## Patrones exigidos por el PIA

| Patrón | Dónde |
|---|---|
| Domain Model / DDD | `src/domain/*` |
| **Specification** (AND / OR / NOT, con `reasons()`) | `common.py` (`Specification`, `&`, `|`, `~`); catálogo en `specifications.py` y `agenda.py` (`SalaLibreSpec`, `InicioFuturoSpec`) |
| **State Machine** (tabla estado × acción) | `common.py::StateMachine`; `MAQUINA_ORDEN`, `MAQUINA_HOSPITALIZACION`, `MAQUINA_CITA` |
| **Domain Events** (publicados *después* del commit) | `events.py`, `uow.py`, `event_bus.py` |
| Repository + Unit of Work | `repositories.py`, `uow.py` |
| Service Layer delgada | `application/services.py` |

## Principios SOLID

Ver [SOLID.md](SOLID.md): cada principio con código real y la prueba que lo verifica (`tests/unit/test_arquitectura.py` comprueba la regla de dependencia).

## Máquinas de estado

```mermaid
stateDiagram-v2
    direction LR
    [*] --> SOLICITADA
    SOLICITADA --> CONFIRMADA: aprobar<br/>[puede_procesarse]
    CONFIRMADA --> REALIZADA: completar
    SOLICITADA --> CANCELADA: cancelar
    CONFIRMADA --> CANCELADA: cancelar
    REALIZADA --> [*]
    CANCELADA --> [*]
```

```mermaid
stateDiagram-v2
    direction LR
    [*] --> HOSPITALIZADO: ingresar (jaula ocupada)
    HOSPITALIZADO --> PENDIENTE_VALIDACION_CRUZADA: FIRMAR_ALTA (veterinario)
    HOSPITALIZADO --> PENDIENTE_VALIDACION_CRUZADA: LIQUIDAR_CUENTA (recepción)
    PENDIENTE_VALIDACION_CRUZADA --> EGRESADO: EGRESAR<br/>[alta firmada AND cuenta liquidada] → jaula libre
    EGRESADO --> [*]
```

```mermaid
stateDiagram-v2
    direction LR
    [*] --> PROGRAMADA: agendar (sala libre)
    PROGRAMADA --> ATENDIDA: atender
    PROGRAMADA --> CANCELADA: cancelar (libera sala; tardía si < 4 h)
```

## Secuencias clave

**RN-04 — prescripción segura (US06)**

```mermaid
sequenceDiagram
    participant API as POST /consultas/{id}/recetas
    participant S as ConsultaService
    participant U as UnitOfWork
    participant D as ServicioValidacionAlergias
    participant B as EventBus
    API->>S: prescribir(...)
    S->>U: cargar Consulta y Paciente
    S->>D: prescribir(consulta, paciente, medicamento, justificación?)
    alt alérgeno coincide y sin justificación
        D-->>S: AlergiaBloqueoError(BloqueoAlergiaDisparadoEvent)
        S->>U: rollback()
        S->>B: publish(BloqueoAlergiaDisparadoEvent)  (auditoría)
        S-->>API: 409 AlergiaBloqueoError
    else sin alergia o con justificación + cédula (ADR-002)
        D->>D: consulta.agregar_a_receta(...)
        S->>U: save + commit()
        U->>B: publish eventos (post-commit)
        S-->>API: 201 consulta
    end
```

**RN-06 — alta hospitalaria cruzada (US11)**

```mermaid
sequenceDiagram
    participant Vet as Veterinario
    participant Rec as Recepción
    participant S as HospitalizacionService
    participant D as ServicioAltaHospitalaria
    Vet->>S: alta-medica(cédula)
    S->>D: procesar(FIRMAR_ALTA)
    D-->>S: PENDIENTE_VALIDACION_CRUZADA (jaula sigue ocupada)
    Rec->>S: liquidacion()
    S->>D: procesar(LIQUIDAR_CUENTA)
    D->>D: apto_para_egreso() = alta AND cuenta
    D-->>S: EGRESO_CONCLUIDO → Jaula.liberar() → JaulaLiberadaEvent
```

## Modelo de persistencia

Una tabla por agregado: columnas indexadas para consultar (`paciente_id`, `estado`, `inicio`…) + columna `doc`
(JSON en SQLite, **JSONB en PostgreSQL**) con el agregado completo serializado por `codec.py` — [ADR-003](adr/ADR-003-persistencia-documento-json.md).

```mermaid
erDiagram
    tutores ||--o{ pacientes : "tutor_id"
    pacientes ||--o{ consultas : "paciente_id"
    pacientes ||--o{ hospitalizaciones : "paciente_id"
    pacientes ||--o{ registros_vacuna : "paciente_id"
    pacientes ||--o{ citas : "paciente_id"
    jaulas ||--o| hospitalizaciones : "jaula_id (en doc)"
    tutores ||--o{ ordenes_servicio : "tutor_id"
    servicios }o--o{ ordenes_servicio : "líneas (en doc)"
```

## Despliegue

`Dockerfile` multi-etapa (`base` → `test` / `app`), `docker-compose.yml` (db + app + tests), CI en GitHub Actions
(`.github/workflows/ci.yml`: pruebas con PostgreSQL de servicio, cobertura ≥ 80 %, exportación de OpenAPI, build de imagen y *deploy hook*)
y `render.yaml` (Blueprint: PostgreSQL + servicio web Docker). Configuración 100 % por variables de entorno (`.env.example`).
