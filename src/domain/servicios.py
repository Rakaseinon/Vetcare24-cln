"""Domain Services: coordinan reglas que involucran más de un agregado (ADR-001)."""
from __future__ import annotations

from datetime import datetime

from .common import AlergiaBloqueoError, BusinessRuleViolation, new_id
from .consulta import Consulta, JustificacionClinica, MedicamentoDosificado
from .events import BloqueoAlergiaDisparadoEvent
from .hospitalizacion import Hospitalizacion, Jaula, TipoJaula
from .paciente import Paciente
from .specifications import AlergenoCoincideSpec


class ServicioValidacionAlergias:
    """RN-04: bloquea la receta si el principio activo coincide con una alergia del paciente.

    Excepción documentada (ADR-002): el veterinario puede continuar solo con justificación clínica formal
    bajo su cédula (según la entrevista con el Director Médico).
    """

    def prescribir(self, consulta: Consulta, paciente: Paciente, medicamento: MedicamentoDosificado,
                   justificacion: JustificacionClinica | None = None) -> None:
        coincide = AlergenoCoincideSpec(paciente.alergenos).is_satisfied_by(medicamento.principio_activo)
        if coincide and justificacion is None:
            raise AlergiaBloqueoError(
                f"BLOQUEO DE SEGURIDAD (RN-04): el paciente es alérgico a '{medicamento.principio_activo}'",
                BloqueoAlergiaDisparadoEvent(paciente_id=paciente.id, principio_activo=medicamento.principio_activo,
                                             consulta_id=consulta.id))
        consulta.agregar_a_receta(medicamento, justificacion if coincide else None)


class ServicioIngresoHospitalario:
    """Asigna jaula compatible y crea la hospitalización (US09)."""

    def ingresar(self, paciente: Paciente, jaula: Jaula, plan: str, contagioso: bool, ahora: datetime,
                 critico: bool = False) -> Hospitalizacion:
        if not jaula.libre:
            raise BusinessRuleViolation(f"La jaula {jaula.id} no está desocupada")
        if contagioso and jaula.tipo is not TipoJaula.AISLAMIENTO:
            raise BusinessRuleViolation("Los pacientes contagiosos solo pueden ingresar a módulos de aislamiento")
        if not contagioso and jaula.tipo is TipoJaula.AISLAMIENTO:
            raise BusinessRuleViolation("Los módulos de aislamiento se reservan para pacientes contagiosos")
        if not contagioso and jaula.tipo.value != paciente.especie:
            raise BusinessRuleViolation(
                f"La jaula {jaula.id} ({jaula.tipo.value}) no corresponde a la especie {paciente.especie}")
        h = Hospitalizacion.ingresar(new_id("HOS"), paciente.id, jaula.id, plan, ahora, critico)
        jaula.ocupar(h.id)
        return h


class ServicioAltaHospitalaria:
    """RN-06: valida la convergencia de alta médica + cuenta liquidada y libera la jaula."""

    PENDIENTE = "PENDIENTE_VALIDACION_CRUZADA"
    CONCLUIDO = "EGRESO_CONCLUIDO"

    def procesar(self, hosp: Hospitalizacion, jaula: Jaula, accion_origen: str, ahora: datetime,
                 cedula: str | None = None) -> str:
        if accion_origen == "FIRMAR_ALTA":
            hosp.firmar_alta_medica(cedula or "")
        elif accion_origen == "LIQUIDAR_CUENTA":
            hosp.liquidar_cuenta()
        else:
            raise BusinessRuleViolation(f"Acción de alta desconocida: {accion_origen}")
        if hosp.intentar_egreso(ahora):
            jaula.liberar()
            return self.CONCLUIDO
        return self.PENDIENTE
