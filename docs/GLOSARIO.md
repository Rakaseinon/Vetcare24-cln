# Glosario de dominio (Lenguaje Ubicuo)

Definiciones formales del equipo (`docs/analisis/originales/GLOSARIO_VETCARE_EQUIPO4.pdf`) con su correspondencia en el código.

| # | Término | Definición | En el código |
|---|---|---|---|
| 1 | Propietario (Tutor) | Persona legalmente responsable de la mascota y de las obligaciones financieras | `Tutor`, `TutorResponsable` |
| 2 | Paciente (Mascota) | Animal registrado que recibe servicios preventivos, terapéuticos o quirúrgicos | `Paciente` |
| 3 | Expediente Clínico Digital | Conjunto consolidado e inmutable de notas, diagnósticos, resultados y tratamientos | `GET /pacientes/{id}/expediente` |
| 4 | Triage Veterinario | Clasificación por gravedad: Rojo / Amarillo / Verde | `NivelTriage`, `HojaTriaje` |
| 5 | Anamnesis | Información retrospectiva obtenida del propietario | campo `S` de `NotaSOAP` |
| 6 | Signos Vitales | Temperatura, frecuencia cardíaca y respiratoria, peso… | `ConstantesVitales`, `Peso` |
| 7 | Nota de Evolución (SOAP) | Asiento médico Subjetivo-Objetivo-Análisis-Plan | `NotaSOAP` |
| 8 | Nota de Enmienda | Addendum que corrige un registro cerrado sin alterarlo | `NotaEnmienda` |
| 9 | Calendario Profiláctico | Cronograma de intervenciones preventivas | `RegistroVacuna.programacion` |
| 10 | Refuerzo (Booster) | Dosis subsecuente tras 21, 28 o 365 días | `IntervaloRefuerzo` |
| 11 | Lote de Biológico | Código del fabricante para farmacovigilancia | `LoteBiologico`, `MarcaVacuna` |
| 12 | Prescripción Terapéutica | Fármaco, dosis por kg, vía, frecuencia y duración | `MedicamentoDosificado` |
| 13 | Alerta de Alergia | Bloqueo/advertencia por principio activo incompatible | `ServicioValidacionAlergias` |
| 14 | Hospitalización | Internamiento continuo para observación o fluidoterapia | `Hospitalizacion`, `Jaula` |
| 15 | Bitácora de Monitoreo | Registro cada 2–4 h de constantes y consumos | `Hospitalizacion.bitacora` |
| 16 | Alta Médica | Dictamen del veterinario que certifica el egreso | `Hospitalizacion.firmar_alta_medica` |
| 17 | Cita Diferenciada | Reserva cuya duración y recurso varían por procedimiento | `Cita`, `TipoServicioAgenda` |
| 18 | Consentimiento Informado | Documento del propietario que autoriza intervenciones | *fuera de alcance de esta entrega* |
| 19 | Registro Duplicado | Misma mascota/tutor con más de un identificador | microchip único + búsqueda predictiva |
| 20 | KPI Clínico | Ocupación de jaulas, retención de vacunas, esperas | `GET /reportes/operativo` |
| — | Cuenta liquidada / Precuenta | Consumos auditados por recepción como condición de egreso | `Hospitalizacion.precuenta_total`, `CuentaLiquidadaEvent` |
| — | Orden de servicio | Solicitud de servicios del tutor (modelo del paquete de datos) | `OrdenServicio` |
