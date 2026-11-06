# Principios SOLID aplicados en VetCare 24

Cada principio se muestra con **código real del repositorio** y con la **prueba que lo verifica**. Las rutas son relativas a la raíz.

| Principio | Dónde se ve | Cómo se comprueba |
|---|---|---|
| **S** — Responsabilidad única | Un agregado por regla de negocio; un servicio de dominio por proceso; controladores sin lógica | `tests/unit/test_*.py` prueban cada pieza aislada |
| **O** — Abierto/cerrado | `Specification` (AND/OR/NOT), `StateMachine` por tabla, `DocRepository` genérico | `tests/unit/test_specification.py`, `test_state_machine.py` |
| **L** — Sustitución de Liskov | `And/Or/NotSpecification` son `Specification`; cualquier notificador o bus cumple los puertos | `tests/unit/test_arquitectura.py::test_la_aplicacion_acepta_cualquier_implementacion_de_los_puertos` |
| **I** — Segregación de interfaces | Puertos pequeños: `EventBus`, `Notificador`, `UnitOfWork` | `src/application/ports.py` (3 `Protocol`, 1–2 métodos los dos primeros) |
| **D** — Inversión de dependencias | `application` depende de puertos; `infrastructure` los implementa; `api/container.py` los conecta | `tests/unit/test_arquitectura.py::test_ninguna_capa_importa_hacia_afuera` (analiza los `import` de todo `src/`) |

## S — Responsabilidad única
Cada clase tiene **una razón para cambiar**:

- `Consulta` solo conoce la nota SOAP, la receta, las enmiendas y los estudios de **una consulta** (RN-01, RN-02). No sabe de camas ni de cobros.
- `ServicioValidacionAlergias`, `ServicioIngresoHospitalario` y `ServicioAltaHospitalaria` (`src/domain/servicios.py`) son servicios de dominio de **una sola regla** cada uno: RN-04, asignación de jaula y RN-06.
- Los servicios de aplicación (`src/application/services.py`) solo orquestan: *cargar → invocar al dominio → guardar → commit*. Las reglas no viven ahí.
- Los controladores (`src/api/routes.py`) validan el contrato y delegan; la documentación de Swagger está aparte (`src/api/docs.py`).

## O — Abierto para extender, cerrado para modificar
- **Specification.** Una regla nueva es una clase nueva que se compone con `&`, `|` o `~`; los operadores (`AndSpecification`, `OrSpecification`, `NotSpecification` en `src/domain/common.py`) y el agregado no cambian. Ejemplo real: `SalaLibreSpec` e `InicioFuturoSpec` (`src/domain/agenda.py`) se añadieron para US02 sin tocar nada de lo anterior.
- **State Machine.** Un estado o acción nuevos son **una fila más** en la tabla `(estado, acción) → estado` (`MAQUINA_ORDEN`, `MAQUINA_HOSPITALIZACION`, `MAQUINA_CITA`); `StateMachine.fire()` no cambia.
- **Repositorios.** `DocRepository[A]` (`src/infrastructure/repositories.py`) ya sabe guardar, leer y contar; un agregado nuevo solo declara su tabla (`row`) y sus columnas indexadas (`_cols`). `CitaRepository` se agregó así.

## L — Sustitución de Liskov
- `AndSpecification`, `OrSpecification` y `NotSpecification` pueden usarse donde se espera cualquier `Specification[T]` (incluida otra composición) y respetan el mismo contrato: `is_satisfied_by` devuelve `bool` y `reasons` lista los motivos. Así `TutorActivo & OrdenConLineas & OrdenAutorizada` es, a su vez, una `Specification`.
- Los servicios de aplicación reciben un `Notificador` y un `EventBus` por su **protocolo**. La prueba `test_la_aplicacion_acepta_cualquier_implementacion_de_los_puertos` reemplaza el notificador real por uno distinto y el caso de uso funciona igual.
- Los repositorios de SQLite y de PostgreSQL son intercambiables: la misma suite (343 pruebas) pasa en ambos motores.

## I — Segregación de interfaces
`src/application/ports.py` no ofrece una «interfaz gigante»: cada colaborador tiene la suya y solo expone lo que el servicio necesita.

```python
class EventBus(Protocol):      # publish, publish_all
class Notificador(Protocol):   # enviar(canal, destino, mensaje)
class UnitOfWork(Protocol):    # repositorios + commit / rollback
```
Quien solo necesita avisar al tutor depende de `Notificador` (1 método), no del bus ni de la base de datos.

## D — Inversión de dependencias
La flecha de dependencia apunta **hacia el dominio**: `api → application → domain ← infrastructure`.

- `domain` no importa nada de `application`, `infrastructure` ni `api`, ni frameworks (`fastapi`, `sqlalchemy`, `pydantic`).
- `application` depende de los puertos (`UowFactory`, `EventBus`, `Notificador`), no de SQLAlchemy.
- La **raíz de composición** `src/api/container.py::build_container` es el único sitio que une servicios con `SqlAlchemyUnitOfWork`, `InMemoryEventBus` y `LogNotificador`.
- No es una promesa de diseño: `tests/unit/test_arquitectura.py` recorre los `import` de cada archivo de `src/` y **falla** si una capa depende de otra hacia afuera.

## Límites honestos
- `UnitOfWork` expone los repositorios como atributos (`Any`) para mantener el código simple; en un proyecto mayor se tiparía cada repositorio con su propio puerto.
- Los servicios de aplicación todavía son clases grandes por módulo (p. ej. `ConsultaService`); si crecen, se partirían por caso de uso.
