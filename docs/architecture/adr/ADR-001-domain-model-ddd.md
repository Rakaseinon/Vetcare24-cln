# ADR-001 — Patrón de lógica de negocio: Domain Model (DDD)

- **Estatus:** Aprobado · **Fecha:** 2026-10-13
- **Autores:** Equipo 4 — Giovani Patiño, Aldo Romero, Leonardo Muñiz (FIME-UANL)
- **Origen:** Reporte U3-FO3 «Diseño Arquitectural del Sistema» (texto completo en `docs/analisis/originales/REPORTE_EQUIPO4_VETCARE.pdf`)

## Contexto
Las reglas RN-01…RN-06 (inmutabilidad médica, Código Rojo, trazabilidad de biológicos, bloqueo por alergia, propiedad del historial y alta cruzada)
son invariantes entrelazadas con ciclo de vida de estados. ¿Qué patrón debe gobernar la lógica para cumplirlas sin fugas hacia BD o UI?

## Opciones evaluadas
| Criterio | Transaction Script | Table Module | **Domain Model (DDD)** |
|---|---|---|---|
| Encapsulamiento de invariantes | Vulnerable | Moderado | **Robusto** |
| Mantenibilidad | Baja | Media | **Alta** |
| Testabilidad unitaria | Difícil | Requiere BD | **Excelente** |
| Garantía de inmutabilidad (RN-01) | Difícil de auditar | Riesgo de UPDATE directo | **Garantizada** |

## Decisión
**Domain Model** con cuatro agregados (Paciente, Consulta, Hospitalización, Profilaxis), servicios de dominio
(`ServicioValidacionAlergias`, `ServicioAltaHospitalaria`), eventos de dominio y una Service Layer delgada con `UnitOfWork`.

## Consecuencias
- (+) Reglas autoprotegidas, auditoría clínica, pruebas de dominio en milisegundos.
- (−) Complejidad de mapeo → patrón Repository (ver ADR-003). Riesgo de fugas a la capa de aplicación → revisión de código.

## Cumplimiento verificado en la implementación
- Cobertura de pruebas de `src/domain` = **100 %** (meta del ADR: ≥ 90 %).
- Auditoría de la Service Layer: las reglas de negocio puras (tutor inactivo, urgencia sin paciente) se movieron a métodos del dominio
  (`Tutor.asegurar_activo`, `Consulta.paciente_requerido`). Quedan en aplicación únicamente comprobaciones de **unicidad que requieren consultar
  repositorios** (microchip duplicado, hospitalización activa única) y validaciones de forma del contrato.
