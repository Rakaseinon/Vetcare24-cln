# ADR-005 — Specification y State Machine explícitas

- **Estatus:** Aceptado · **Fecha:** 2026-11-01 · **Requisito:** PIA (≥ 3 Specifications con AND/OR/NOT, máquina de estados, eventos)

## Contexto
Varias reglas del BRD son combinaciones de condiciones (puede procesarse una orden si el tutor está activo **y** tiene líneas **y** está autorizada;
beneficio si es preferente **y** supera el mínimo **y no** tiene promoción) y varios agregados tienen ciclo de vida (orden, hospitalización, cita).
Con `if` anidados dentro de los servicios, la regla se repite, no se puede probar por separado y no explica por qué falló.

## Decisión
- `Specification[T]` con operadores `&`, `|`, `~` y `reasons()` (nombra *cada* regla incumplida; así la API responde «tutor_activo, orden_autorizada…» y no un booleano opaco).
- `StateMachine` basada en tabla `(estado, acción) → estado`; los agregados llaman `fire()` y los estados inválidos lanzan `InvalidStateTransition` (HTTP 409).
- Las reglas del paquete de datos (`puede_procesarse`, `beneficio_referencia`) se componen como `TutorActivo & OrdenConLineas & OrdenAutorizada` y `TutorPreferente & TotalMinimo & ~PromocionActiva`.

## Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| `if/else` dentro de cada servicio | Reglas duplicadas, difíciles de probar y sin motivo explícito del rechazo |
| Biblioteca externa de máquinas de estado (p. ej. `transitions`) | Dependencia adicional para 3 tablas pequeñas; una tabla propia es más simple de defender y de exportar a diagramas |
| Estados como banderas booleanas sueltas | Permite combinaciones imposibles (p. ej. «cancelada y realizada») |

## Consecuencias
Reglas legibles y testeables por separado; la tabla de transiciones se exporta (`tabla()`) para documentar diagramas sin desincronizarse del código.
(−) Hay que mantener la disciplina de no saltarse `fire()`; las pruebas de estado cubren cada transición válida e inválida.
