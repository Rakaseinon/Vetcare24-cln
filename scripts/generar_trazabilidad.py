"""Genera docs/TRAZABILIDAD.md (BRD / User Story / Gherkin / BPMN -> dominio -> código -> pruebas).

La tabla de abajo es la FUENTE; el documento se regenera con:   python scripts/generar_trazabilidad.py
`tests/unit/test_trazabilidad.py` verifica en CI que (1) cada archivo y símbolo citado existe y (2) el .md está al día.
Formato de referencia: "ruta/archivo.py::Simbolo".  Los símbolos son clases, funciones, métodos o constantes.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

D = "src/domain/"
S = "src/application/services.py::"
R = "src/api/routes.py::"
TU, TC, TH, TP, TA, TS, TO_ = (f"tests/unit/test_{n}.py::" for n in
                                ("paciente_tutor", "consulta", "hospitalizacion", "profilaxis", "agenda",
                                 "state_machine", "orden_servicio"))
IC = "tests/integration/test_api_clinica.py::"
IA = "tests/integration/test_api_agenda_laboratorio.py::"
IO = "tests/integration/test_oraculo_paquete_datos.py::"

# (id, fuente/BRD, escenario Gherkin, BPMN, dominio, código, pruebas)
FILAS = [
    ("US01", "BRD §3.1 Gestión de Identidad · Mód. 1",
     "Registro exitoso de mascota asociada", "Recepción: ficha de admisión (DO_01)",
     [D + "tutor.py::Tutor", D + "paciente.py::Paciente"],
     [S + "PacienteService", R + "registrar_mascota", R + "crear_tutor"],
     [TU + "test_tutor_requiere_contacto_y_canal_valido", TU + "test_registro_paciente_normaliza_y_emite_evento",
      TU + "test_registro_invalido", IC + "test_us01_registro_y_busqueda_por_microchip_y_nombre"]),
    ("US12 / RF-01", "BRD RF-01 · Mód. 1",
     "Coincidencia predictiva de expedientes", "Búsqueda unificada de paciente",
     [D + "paciente.py::MicrochipCode"],
     [S + "PacienteService", "src/infrastructure/repositories.py::PacienteRepository", R + "buscar_pacientes"],
     [IC + "test_us01_registro_y_busqueda_por_microchip_y_nombre"]),
    ("US02 / RF-03", "BRD §3.1 Agenda Inteligente · Mód. 2",
     "Bloqueo de horario según servicio (cirugía mayor = 90 min + quirófano)", "Asignación dinámica en agenda",
     [D + "agenda.py::Cita", D + "agenda.py::ServicioAgenda", D + "agenda.py::SalaLibreSpec",
      D + "agenda.py::MAQUINA_CITA"],
     [S + "AgendaService", R + "agendar_cita", R + "cancelar_cita"],
     [TA + "test_bloqueo_segun_servicio", TA + "test_cirugia_mayor_bloquea_90_y_asigna_quirofano",
      TA + "test_quirofanos_agotados_con_sobrecupo_evitado", TA + "test_politica_de_cancelacion_4h",
      IA + "test_us02_cirugia_mayor_reserva_90_min_y_asigna_quirofano", IA + "test_us02_sobrecupo_409_y_cancelar_libera"]),
    ("US03 / RN-02", "BRD RN-02 · Mód. 2",
     "Admisión de urgencia crítica", "Activar botón «Admisión Urgencia» (Código Rojo)",
     [D + "consulta.py::Consulta", D + "events.py::AdmisionUrgenciaActivadaEvent"],
     [S + "ConsultaService", R + "admitir_urgencia"],
     ["tests/unit/test_consulta.py::test_urgencia_no_exige_datos_administrativos_y_es_rojo",
      IC + "test_rn02_urgencia_sin_datos_administrativos_y_regularizacion",
      IC + "test_urgencia_sin_regularizar_no_puede_prescribir_ni_pedir_laboratorio"]),
    ("US04 / RF-02", "BRD RF-02 · Mód. 2",
     "Detección de alerta por alergia", "Captura de triaje inicial (peso, temperatura, alergias)",
     [D + "paciente.py::HojaTriaje", D + "paciente.py::Alergeno", D + "paciente.py::Peso"],
     [S + "PacienteService", R + "capturar_triaje"],
     [TU + "test_triaje_actualiza_peso_y_alergias", TU + "test_alergias_sin_duplicados_y_alerta",
      IC + "test_us04_triaje_actualiza_peso_y_alergias"]),
    ("US05 / RN-01", "BRD RN-01 · Mód. 3",
     "Cierre de nota clínica inmutable", "Firmar y cerrar nota SOAP (DO_02)",
     [D + "consulta.py::NotaSOAP", D + "consulta.py::Consulta"],
     [S + "ConsultaService", R + "firmar_nota"],
     ["tests/unit/test_consulta.py::test_firmar_congela_y_registra_cedula",
      "tests/unit/test_consulta.py::test_nota_firmada_no_se_edita_ni_se_refirma_ni_se_receta",
      IC + "test_rn01_nota_firmada_es_inmutable_y_admite_enmiendas"]),
    ("US06 / RN-04", "BRD RN-04 · Mód. 3",
     "Bloqueo por prescripción de sustancia alérgena (+ excepción justificada, ADR-002)",
     "Prescripción farmacológica (validación activa contra alergias, DO_03)",
     [D + "servicios.py::ServicioValidacionAlergias", D + "consulta.py::MedicamentoDosificado",
      D + "specifications.py::AlergenoCoincideSpec"],
     [S + "ConsultaService", R + "prescribir"],
     ["tests/unit/test_consulta.py::test_rn04_bloquea_alergeno_y_no_modifica_receta",
      "tests/unit/test_consulta.py::test_rn04_excepcion_con_justificacion_bajo_cedula",
      "tests/unit/test_consulta.py::test_dosis_calculada_por_peso_y_requiere_peso",
      IC + "test_rn04_bloqueo_justificacion_y_sin_alergia"]),
    ("US07 / RN-03 / RF-04", "BRD RN-03, RF-04 · Mód. 4",
     "Creación de cita profiláctica sugerida (refuerzo a 21 días)",
     "Aplicación de biológico (lote y marca) → cálculo automático de refuerzo",
     [D + "profilaxis.py::RegistroVacuna", D + "profilaxis.py::IntervaloRefuerzo"],
     [S + "ProfilaxisService", R + "registrar_vacuna"],
     [TP + "test_refuerzo_exacto", TP + "test_rn03_sin_lote_o_marca_no_se_registra",
      TP + "test_intervalo_por_edad_y_esquema", IC + "test_rn03_vacuna_exige_lote_y_marca_y_calcula_refuerzo"]),
    ("US08 / RF-05", "BRD RF-05 · Mód. 4",
     "Despacho automatizado de notificación 48 h antes", "Programación de recordatorio",
     [D + "specifications.py::RefuerzoPorNotificarSpec", D + "profilaxis.py::RegistroVacuna"],
     [S + "ProfilaxisService", R + "procesar_recordatorios", "src/infrastructure/notifier.py::LogNotificador"],
     [IC + "test_us08_recordatorio_48h_antes_se_envia_una_sola_vez"]),
    ("US09", "BRD §3.1 Hospitalización 24/7 · Mód. 5",
     "Asignación de jaula/box hospitalario", "Asignación de jaula/box y plan de fluidoterapia",
     [D + "servicios.py::ServicioIngresoHospitalario", D + "hospitalizacion.py::Jaula",
      D + "hospitalizacion.py::Hospitalizacion"],
     [S + "HospitalizacionService", R + "ingresar", R + "listar_jaulas"],
     [TH + "test_ingreso_asigna_jaula_compatible", TH + "test_ingreso_rechaza_jaula_incompatible",
      TH + "test_contagioso_va_a_aislamiento_y_jaula_no_se_ocupa_dos_veces", IC + "test_ingreso_y_ocupacion_de_jaulas"]),
    ("US10 / RF-06", "BRD RF-06 · Mód. 5",
     "Registro de signos fuera de rango", "Monitoreo y registro de signos cada 2–4 h (DO_04)",
     [D + "hospitalizacion.py::ConstantesVitales", D + "specifications.py::LecturaVencidaSpec",
      D + "hospitalizacion.py::Hospitalizacion"],
     [S + "HospitalizacionService", R + "registrar_constantes", R + "lecturas_vencidas"],
     [TH + "test_ventana_4h_estable_y_2h_critico", TH + "test_lectura_anormal_eleva_a_critico_y_emite_evento_luego_normaliza",
      TH + "test_precuenta_suma_consumos", IC + "test_us10_bitacora_alertas_y_precuenta"]),
    ("US11 / RN-06", "BRD RN-06 · Mód. 5",
     "Validación de alta integral (alta médica + cuenta liquidada)",
     "Firma de nota de egreso → auditoría de insumos, liquidación y egreso",
     [D + "servicios.py::ServicioAltaHospitalaria", D + "specifications.py::apto_para_egreso",
      D + "hospitalizacion.py::MAQUINA_HOSPITALIZACION"],
     [S + "HospitalizacionService", R + "firmar_alta", R + "liquidar"],
     [TH + "test_alta_requiere_ambas_confirmaciones_sin_importar_orden",
      TH + "test_no_permite_repetir_firma_ni_liquidacion_ni_actuar_tras_egreso",
      TS + "test_maquina_hospitalizacion_no_egresa_sin_pasar_por_pendiente",
      IC + "test_rn06_alta_cruzada_libera_jaula_solo_con_ambas"]),
    ("US13 / RN-01", "BRD RN-01 · Mód. 3",
     "Anexo de nota de aclaración (enmienda) sobre registro sellado", "Firmar y cerrar nota SOAP (registro inmutable + enmiendas)",
     [D + "consulta.py::NotaEnmienda", D + "events.py::NotaEnmiendaAnexadaEvent"],
     [S + "ConsultaService", R + "anexar_enmienda"],
     ["tests/unit/test_consulta.py::test_enmienda_solo_sobre_nota_firmada_y_conserva_original",
      IC + "test_enmienda_sobre_nota_sin_firmar_es_409", IC + "test_rn01_nota_firmada_es_inmutable_y_admite_enmiendas"]),
    ("US14", "Levantamiento (laboratorio externo) · Mód. 3",
     "Adjuntar reporte de laboratorio y alertar al médico", "— (extensión del Expediente, DO_02)",
     [D + "consulta.py::EstudioLaboratorio", D + "consulta.py::ResultadoLaboratorio",
      D + "events.py::ResultadoLaboratorioAdjuntadoEvent"],
     [S + "ConsultaService", R + "solicitar_estudio", R + "adjuntar_resultado", "src/api/container.py::build_container"],
     ["tests/unit/test_consulta.py::test_us14_solicitar_y_adjuntar_resultado_emite_alerta_al_medico",
      "tests/unit/test_consulta.py::test_us14_resultados_se_anexan_aun_con_nota_firmada",
      IA + "test_us14_laboratorio_flujo_y_alerta_al_medico", IA + "test_us14_validaciones_y_permisos"]),
    ("US15", "BRD §6 KPIs · Mód. 5",
     "Extracción de KPIs semanales (ocupación, citas canceladas, vacunas)", "— (consulta gerencial)",
     [D + "hospitalizacion.py::Jaula", D + "agenda.py::Cita"],
     [S + "ReporteService", R + "reporte"],
     [IC + "test_reporte_operativo_solo_director", IA + "test_cancelacion_tardia_y_kpi_de_citas_canceladas"]),
    ("RN-05", "BRD RN-05", "—", "—",
     [D + "paciente.py::Paciente"], [S + "PacienteService", R + "transferir"],
     [TU + "test_rn05_transferencia_conserva_historial_y_cierra_titularidad",
      IC + "test_rn05_transferencia_de_tutor_conserva_historial"]),
    ("RNF-01", "BRD RNF-01 (< 3 s)", "—", "—", ["src/infrastructure/models.py::PacienteRow"], [R + "expediente"],
     [IC + "test_rnf01_expediente_clinico_abre_en_menos_de_3_segundos"]),
    ("RNF-02", "BRD RNF-02 (24/7)", "—", "—", [], ["src/api/main.py::create_app", "Dockerfile::HEALTHCHECK"],
     [IC + "test_health_y_openapi"]),
    ("RNF-03", "BRD RNF-03 (RBAC)", "—", "—", [], ["src/api/security.py::requiere"],
     [IC + "test_rbac_rechaza", IC + "test_rnf03_recepcion_no_accede_al_detalle_clinico",
      IC + "test_rbac_enfermeria_no_firma_ni_receta_pero_si_registra_constantes",
      IC + "test_rbac_alta_solo_veterinario_y_liquidacion_solo_recepcion"]),
    ("Paquete de datos · regla 1", "LEEME.txt: puede_procesarse = actor activo AND ≥1 línea AND autorización",
     "—", "Flujo SOLICITADA → CONFIRMADA", [D + "specifications.py::puede_procesarse", D + "specifications.py::TutorActivoSpec"],
     [S + "OrdenService", R + "solicitar_orden"],
     [TO_ + "test_puede_procesarse_tabla_de_verdad", TO_ + "test_motivos_nombran_cada_regla_incumplida",
      IO + "test_casos_de_prueba_contra_oraculo"]),
    ("Paquete de datos · regla 2", "LEEME.txt: beneficio_referencia = preferente AND total ≥ 1500 AND NOT promoción",
     "—", "—", [D + "specifications.py::elegible_beneficio_referencia", D + "specifications.py::PromocionActivaSpec"],
     [S + "OrdenService"], [TO_ + "test_beneficio_referencia", IO + "test_casos_de_prueba_contra_oraculo"]),
    ("Paquete de datos · estados", "LEEME.txt: SOLICITADA → CONFIRMADA → REALIZADA / CANCELADA",
     "—", "—", [D + "orden_servicio.py::MAQUINA_ORDEN", D + "orden_servicio.py::OrdenServicio",
                D + "common.py::StateMachine"],
     [S + "OrdenService", R + "transicionar"],
     [TS + "test_transiciones_validas_orden", TS + "test_transiciones_invalidas_orden",
      TO_ + "test_flujo_feliz_y_eventos", IO + "test_transiciones_contra_oraculo",
      IC + "test_orden_por_api_flujo_completo_y_validaciones"]),
    ("Patrón Specification", "PIA: ≥3 Specifications con AND/OR/NOT", "—", "—",
     [D + "common.py::Specification", D + "common.py::AndSpecification", D + "common.py::OrSpecification",
      D + "common.py::NotSpecification"], [], ["tests/unit/test_specification.py::test_and",
                                               "tests/unit/test_specification.py::test_or",
                                               "tests/unit/test_specification.py::test_not",
                                               "tests/unit/test_specification.py::test_razones_de_incumplimiento"]),
    ("Persistencia / 12-Factor", "PIA: persistencia + config por entorno", "—", "—",
     ["src/infrastructure/codec.py::encode"], ["src/infrastructure/db.py::normalizar_url",
                                               "src/infrastructure/config.py::Settings",
                                               "src/infrastructure/uow.py::SqlAlchemyUnitOfWork"],
     ["tests/unit/test_infra_config.py::test_normalizar_url", "tests/unit/test_infra_config.py::test_settings_desde_entorno"]),
]

SIMBOLO = r"^\s*(?:(?:async\s+)?def|class)\s+{n}\b|^{n}\b\s*[:=]|^{n}\s*:\s"


def verificar_referencia(ref: str) -> str | None:
    """None si la referencia existe; texto del error en otro caso."""
    ruta, _, simbolo = ref.partition("::")
    f = ROOT / ruta
    if not f.is_file():
        return f"archivo inexistente: {ruta}"
    if not simbolo:
        return None
    texto = f.read_text(encoding="utf-8")
    if ruta == "Dockerfile":
        return None if simbolo in texto else f"{simbolo} no está en {ruta}"
    if not re.search(SIMBOLO.format(n=re.escape(simbolo)), texto, re.M):
        return f"símbolo inexistente: {ref}"
    return None


def referencias_rotas() -> list[str]:
    malas = []
    for fila in FILAS:
        for grupo in fila[4:]:
            for ref in grupo:
                if (m := verificar_referencia(ref)):
                    malas.append(f"{fila[0]}: {m}")
    return malas


def _lista(refs: list[str]) -> str:
    return "<br>".join(f"`{r.split('/')[-1]}`" for r in refs) if refs else "—"


def render() -> str:
    out = ["# Matriz de trazabilidad", "",
           "> Generado por `scripts/generar_trazabilidad.py`. **No editar a mano.** Una prueba (`tests/unit/test_trazabilidad.py`) "
           "falla en CI si alguna referencia ya no existe o el documento está desactualizado.", "",
           "Cadena: **BRD / User Story / Gherkin / BPMN → dominio → código → pruebas**.", "",
           "| ID | Fuente (BRD / US) | Escenario Gherkin | Elemento BPMN | Dominio (`src/domain`) | Código (aplicación / API) | Pruebas |",
           "|---|---|---|---|---|---|---|"]
    for i, fuente, gherkin, bpmn, dom, cod, pru in FILAS:
        out.append(f"| **{i}** | {fuente} | {gherkin} | {bpmn} | {_lista(dom)} | {_lista(cod)} | {_lista(pru)} |")
    out += ["", "## Cobertura de la matriz", "",
            f"- Filas: **{len(FILAS)}** · User Stories del equipo cubiertas: **US01–US15 (15/15)**.",
            "- Reglas de negocio: RN-01 a RN-06 · Requerimientos: RF-01…RF-06 (RF-03 parcial: ver `DIFERENCIAS_PAQUETE_DATOS.md`) · RNF-01…RNF-03.",
            "- **RNF-04** (vistas responsivas/táctiles) no aplica a un backend REST: queda para el cliente (fuera de alcance de este PIA).",
            "- Referencias verificadas automáticamente: " + str(sum(len(g) for f in FILAS for g in f[4:])) + ".", ""]
    return "\n".join(out)


if __name__ == "__main__":
    rotas = referencias_rotas()
    if rotas:
        print("Referencias rotas:\n  " + "\n  ".join(rotas))
        sys.exit(1)
    destino = ROOT / "docs" / "TRAZABILIDAD.md"
    destino.write_text(render(), encoding="utf-8")
    print(f"{destino} escrito ({len(FILAS)} filas)")
