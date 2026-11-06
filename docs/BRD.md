# BRD — VetCare 24: Sistema de Gestión Clínica y Hospitalaria 24/7

**Equipo 4 · FIME-UANL · Componentes de Lógica de Negocio** — Giovani Aldahir Patiño Rodríguez (2118917), Leonardo Alonso Muñiz Espinosa (2115635), Aldo René Romero Parga (2118748) · Profesor: Miguel Ángel Gómez Marroquín.
*Documento fuente: `docs/analisis/originales/BRD_VETCARE_EQUIPO4.pdf` (U2, 04/09/2026). Esta versión en Markdown lo reproduce y añade el estado de implementación.*

## 1. Contexto
**Modelo operativo.** VetCare 24 es una clínica y centro hospitalario veterinario con atención 24/7: consulta general y de especialidad, medicina preventiva,
cirugía, laboratorio y hospitalización continua. Esquema de **cuenta familiar**: un tutor puede tener varias mascotas, cada una con expediente individual, trazable e independiente.

**Problema (AS-IS).** Registros físicos y digitales fragmentados: expedientes duplicados; consulta lenta de antecedentes/alergias en urgencias;
calendarios de vacunación sin recordatorios; agenda con duraciones estáticas y sin carril de emergencia.

**Visión (TO-BE).** Plataforma centralizada: expedientes unificados tutor-mascotas, agenda por servicio, admisión inmediata de emergencias,
notas médicas inmutables con enmiendas auditadas y motor automático de recordatorios de vacunación.

## 2. Actores
| Actor | Responsabilidad | Necesidad principal |
|---|---|---|
| Recepción | Admisión, agenda, cobros | Buscar rápido sin duplicar fichas; agendar según duración real |
| Médico Veterinario | Diagnóstico, prescripción, cirugía, altas | Historial al instante, notas SOAP inmutables, alertas de alergia |
| Personal Clínico / Enfermería | Cuidados y monitoreo en hospitalización | Capturar signos vitales en rondas, desde tablet |
| Propietario / Tutor | Responsable legal y financiero | Avisos previos a refuerzos; indicaciones de tratamiento |
| Director Médico / Administrador | Supervisión, auditoría, gestión | Auditar enmiendas; monitorear ocupación y cumplimiento de citas |

## 3. Alcance
**Dentro:** gestión de identidad (código correlativo + microchip) · agenda inteligente (15/30/45/90–120 min) · admisión de urgencia ·
expediente clínico digital con bloqueo tras firma y enmiendas · seguridad farmacológica · módulo profiláctico (lote obligatorio, refuerzo 21–28/365 días, notificaciones) ·
hospitalización 24/7 (jaulas, bitácora 2–4 h, validación cruzada de alta) · RBAC.
**Fuera:** facturación electrónica ante entidades tributarias · nómina/asistencia · e-commerce · telemedicina.

## 4. Reglas de negocio
| ID | Regla |
|---|---|
| RN-01 | Una nota firmada se congela; solo se corrige con una **Nota de Enmienda** vinculada (autor, fecha, motivo). |
| RN-02 | El triage rojo salta la lista de espera y los trámites administrativos. |
| RN-03 | Lote y fabricante son obligatorios antes de guardar una vacuna. |
| RN-04 | Advertencia visible y restrictiva si se receta un principio activo registrado como alérgeno (excepción solo con justificación bajo cédula, ver ADR-002). |
| RN-05 | El expediente pertenece al animal: al transferir tutor el historial se conserva y cambian contacto y cobro. |
| RN-06 | Liberar una jaula exige dos firmas: alta médica del veterinario **y** precuenta/cuenta confirmada en recepción. |

## 5. Requerimientos
**Funcionales.** RF-01 búsqueda predictiva (teléfono, mascota, código, microchip) · RF-02 hoja de triaje (peso, temperatura, motivo) ·
RF-03 citas por servicio con bloqueo automático · RF-04 cálculo automático del próximo refuerzo · RF-05 recordatorio 48 h antes ·
RF-06 bitácora de hospitalización en ventanas de 2–4 h.

**No funcionales.** RNF-01 expediente < 3 s · RNF-02 disponibilidad 24/7 · RNF-03 acceso por roles (recepción sin detalle clínico) · RNF-04 vistas táctiles responsivas.

## 6. Criterios de éxito (KPIs)
Duplicados < 1 % · +40 % de retorno a refuerzos · ingreso en código rojo < 15 s · 100 % de pacientes hospitalizados con signos vitales en intervalos ≤ 4 h.

## 7. Estado de implementación (este repositorio)
| Elemento | Estado | Evidencia |
|---|---|---|
| RN-01 … RN-06 | ✅ implementadas y probadas | `docs/TRAZABILIDAD.md` |
| US01 … US15 (15/15) | ✅ | `docs/TRAZABILIDAD.md` |
| RF-01 … RF-06 | ✅ (RF-03: agenda por servicio y sala; sin calendario visual) | `docs/TRAZABILIDAD.md` |
| RNF-01 | ✅ medido en prueba automatizada (< 3 s) | `test_rnf01_…` |
| RNF-02 | ◐ endpoint `/health`, `HEALTHCHECK` Docker y despliegue gestionado; el SLA real depende del proveedor | `Dockerfile`, `render.yaml` |
| RNF-03 | ✅ RBAC por rol (demostrativo, ADR-004) | `test_rbac_*`, `test_rnf03_*` |
| RNF-04 | ➖ no aplica a un backend REST (queda para el cliente web/tablet) | — |
| KPI «código rojo < 15 s» | ◐ la admisión es una sola llamada API (ms); el tiempo de punta a punta depende de la UI | `test_rn02_*` |
| Fuera de alcance de esta entrega | consentimiento informado, lista de espera de cancelaciones, pago en línea de estudios externos, stock crítico de fármacos, alertas sonoras (UI) — ver `DIFERENCIAS_PAQUETE_DATOS.md` | — |
