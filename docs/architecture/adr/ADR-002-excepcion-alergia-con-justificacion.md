# ADR-002 — Bloqueo por alergia con excepción justificada bajo cédula

- **Estatus:** Aceptado · **Fecha:** 2026-11-01 · **Reglas:** RN-04, US06

## Contexto
El BRD pide un bloqueo *restrictivo* (RN-04). En la entrevista el Director Médico precisó: el aviso no puede ser ignorable, y la receta
**no se confirma salvo que el veterinario capture una justificación clínica formal bajo su propia cédula**.

## Decisión
`ServicioValidacionAlergias.prescribir` (dominio):
1. Si el principio activo coincide con un alérgeno del paciente **y no hay justificación** → lanza `AlergiaBloqueoError`
   (HTTP 409) con el evento `BloqueoAlergiaDisparadoEvent`; la receta no cambia.
2. Con `JustificacionClinica(texto, CedulaProfesional)` válida → agrega el ítem y emite `PrescripcionConAlergiaJustificadaEvent`.
3. La capa de aplicación hace `rollback()` y **publica el evento de bloqueo igualmente** para dejar rastro de auditoría.

## Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| Aviso informativo que el médico puede ignorar | Contradice RN-04 y la entrevista con el Director Médico: un aviso ignorable no protege al paciente |
| Bloqueo absoluto sin excepción | Hay casos clínicos reales (sin alternativa terapéutica) en que el veterinario debe poder continuar |
| Aprobación de un segundo veterinario | Añade una espera inaceptable en urgencias y no aparece en el levantamiento |

## Consecuencias
(+) Cumple RN-04 y la excepción clínica real; auditoría de cada intento. (−) El cliente debe ofrecer el flujo de justificación (la API ya lo expone en `RecetaIn`).
(−) La cédula se valida solo por formato; verificar su vigencia ante la SEP queda fuera del alcance.
