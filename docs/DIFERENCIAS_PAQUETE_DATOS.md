# Diferencias, supuestos y límites

El `LEEME.txt` del paquete de datos indica: *«las reglas, estados e importes son un modelo de pruebas propuesto… si difieren del BRD/US/BPMN del equipo,
documentar las diferencias y adaptar fixtures y oráculos; no reemplazar los requerimientos propios»*. Este documento cumple esa indicación.

## 1. Paquete de datos vs. modelo del equipo

| Tema | Paquete VetCare 24 | Decisión en este proyecto |
|---|---|---|
| Entidades | actor = tutor · recurso = servicio veterinario · operación = orden | El BRD del equipo no define «orden de servicio» ni catálogo con precios. Se modela como agregado **separado** `OrdenServicio` (+ `ServicioCatalogo`) sin tocar los 4 agregados clínicos del ADR-001. |
| `puede_procesarse` | regla ilustrativa: actor activo AND ≥1 línea AND autorización | Implementada tal cual (`TutorActivo & OrdenConLineas & OrdenAutorizada`). Las «precondiciones de ejemplo» `veterinario_disponible` y `mascota_registrada` **no** se aplican (no están en la regla numerada ni hay datos para evaluarlas). |
| `beneficio_referencia` | preferente AND total ≥ 1 500 MXN AND NOT promoción | Implementada con `Decimal` (borde inclusivo: 1 500.00 aplica, 1 499.99 no). |
| Flujo de estados | SOLICITADA → CONFIRMADA → REALIZADA → CANCELADA; alternativa SOLICITADA → CANCELADA | Interpretación: `aprobar` S→C, `completar` C→R, `cancelar` desde S o C. **REALIZADA y CANCELADA son terminales** (un servicio ya realizado no se cancela). `aprobar` exige `puede_procesarse`. |
| Órdenes sin líneas | VET-O013 y VET-O039 no tienen detalle | Se cargan con 0 líneas → inválidas por la regla 1 (comportamiento esperado por el oráculo). |
| Datos históricos | Seis órdenes (VET-O005, O015, O020, O035, O040, O055) incluyen el servicio deshabilitado VET-P011; ninguna línea excede la «capacidad» | Las órdenes del paquete se **cargan tal cual** (son datos de prueba) y `puede_procesarse` **no** evalúa el catálogo (la regla 1 del LEEME no lo menciona); las validaciones de cantidad > 0, capacidad y servicio habilitado aplican a órdenes **nuevas** (`POST /ordenes`). |
| Oráculo | — | `tests/integration/test_oraculo_paquete_datos.py` recalcula los resultados solo con `csv` + `Decimal` (sin importar `src.domain`) y los compara con la API: 120 casos + 20 transiciones. |
| Resultado de transiciones | `repetir_aprobacion`, `saltar_estado` | `repetir_aprobacion`: la 2.ª aprobación → 409 (`InvalidStateTransition`); `saltar_estado` (completar desde SOLICITADA) → 409. |

## 2. User Stories / Gherkin vs. implementación

| US | Diferencia | Motivo / estado |
|---|---|---|
| US13 | Gherkin: «consulta cerrada **hace más de 24 h**». RN-01 y ADR-001 no fijan plazo. | Se permite la enmienda en **cualquier momento** posterior a la firma (más general y consistente con RN-01). Pendiente de confirmar con el equipo si se desea el umbral de 24 h. |
| US13 | La historia dice «director Médico»; el Gherkin dice «el médico». | Pueden anexar `VETERINARIO` y `DIRECTOR`. |
| US12 | Gherkin: lista de coincidencias «con foto y teléfono». | Se devuelven teléfono del tutor y datos de la mascota; **no hay foto** (sin almacenamiento de archivos). |
| US07 / RF-04 | «21 días exactos»; BRD: 21–28 d base y 365 d anual. | Esquemas `CACHORRO_21`, `CACHORRO_28`, `ANUAL`. Sin esquema explícito: < 12 meses → 21 d; adultos o edad desconocida → 365 d (**supuesto** a validar con el Director Médico). |
| US08 | El mensaje debe incluir «enlace para confirmar o reagendar». | Se despacha el aviso por el canal preferido (WhatsApp/correo) **sin enlace** (requiere cliente web). El proveedor real de mensajería es simulado (`LogNotificador`). |
| US10 | «Aviso sonoro/visual en la central de enfermería». | La API marca la hospitalización como `CRITICO` y emite `SignosVitalesFueraDeRangoEvent`; el sonido/pantalla es responsabilidad de la UI. **Rangos de referencia** (temperatura 37.5–39.5 °C, FC 60–180, FR 10–40) son un **supuesto técnico no validado clínicamente**; deben confirmarse con el Director Médico y variar por especie. |
| US11 | Estado «Alta Médica» y «desbloquea resumen para facturación». | El estado final es `EGRESADO` vía `PENDIENTE_VALIDACION_CRUZADA`; la facturación electrónica está **fuera de alcance** del BRD (se expone `precuenta_total`). |
| US14 | Subir el **PDF** del hemograma. | Se registra **metadato + SHA-256** (extensión validada: .pdf/.png/.jpg/.jpeg); no se guardan binarios. Almacenamiento de archivos = trabajo futuro. La «solicitud de estudios externos con pago en línea» del levantamiento no se implementa. |
| US15 | «Gráficos… y stock de biológicos consumidos». | La API devuelve KPIs numéricos (ocupación, vacunas aplicadas, refuerzos pendientes, citas e órdenes canceladas); **no hay gráficos ni inventario de biológicos**. |
| US02 | Calendario, lista de espera de cancelaciones, consentimiento informado. | Implementados: bloqueo por servicio, sala/quirófano sin solapes, cancelación tardía < 4 h. **No** implementados: calendario visual, lista de espera, consentimiento informado. |
| ADR-001 | Cobertura ≥ 90 % en métodos de dominio; BRD/PIA ≥ 80 %. | Dominio 100 %, total ≈ 99 % (ver README). |
| ADR-001 | «Rechazo de PRs con lógica de negocio en la Service Layer». | Auditado: reglas puras movidas al dominio. Permanecen en aplicación las verificaciones de unicidad que requieren repositorio (microchip, hospitalización activa) — documentado en ADR-001. |
| BRD §6 | KPIs de negocio (duplicados < 1 %, +40 % de retorno, código rojo < 15 s). | Son métricas de operación en producción; el sistema provee los datos pero **no se pueden demostrar con datos ficticios**. |

## 3. Supuestos técnicos
- Fechas/horas en **UTC**; una hora sin zona se interpreta como UTC (`agenda.a_utc`).
- Autenticación: encabezado `X-Rol` solo demostrativo (ADR-004). No hay usuarios, contraseñas ni JWT.
- Las 20 jaulas (12 perro, 6 gato, 2 aislamiento) y las 3 salas de consulta + 2 quirófanos son configuración fija en el código (`seed.py`, `agenda.py`).
- Los datos del paquete son ficticios; no se almacenan datos personales reales.
