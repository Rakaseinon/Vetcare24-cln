"""ConsultaAggregate (raíz: Consulta). RN-01 inmutabilidad, enmiendas, receta, admisión de urgencia (RN-02)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

from .common import (AggregateRoot, BusinessRuleViolation, EntityNotFound, NotaInmutableError,
                     ValidationDomainError, new_id, require_text, utcnow)
from .events import (AdmisionUrgenciaActivadaEvent, EstudioLaboratorioSolicitadoEvent, NotaEnmiendaAnexadaEvent,
                     NotaSOAPFirmadaEvent, PrescripcionConAlergiaJustificadaEvent,
                     ResultadoLaboratorioAdjuntadoEvent)
from .paciente import NivelTriage, Peso


class EstadoNota(str, Enum):
    BORRADOR = "BORRADOR"
    CONGELADA = "CONGELADA"


@dataclass(frozen=True)
class CedulaProfesional:
    numero: str

    def __post_init__(self) -> None:
        n = str(self.numero).strip()
        if not re.fullmatch(r"\d{7,8}", n):
            raise ValidationDomainError("La cédula profesional debe tener 7 u 8 dígitos")
        object.__setattr__(self, "numero", n)


@dataclass(frozen=True)
class JustificacionClinica:
    texto: str
    cedula: CedulaProfesional

    def __post_init__(self) -> None:
        require_text(self.texto, "justificacion")


@dataclass(frozen=True)
class MedicamentoDosificado:
    principio_activo: str
    dosis_mg_por_kg: Decimal
    via: str
    frecuencia_horas: int
    duracion_dias: int
    dosis_calculada_mg: Decimal

    @classmethod
    def para_peso(cls, principio_activo: str, dosis_mg_por_kg: Decimal | float | str, via: str,
                  frecuencia_horas: int, duracion_dias: int, peso: Peso | None) -> "MedicamentoDosificado":
        if peso is None:
            raise ValidationDomainError("El peso del paciente es indispensable para dosificar (RF-02)")
        try:
            d = Decimal(str(dosis_mg_por_kg))
        except InvalidOperation:
            raise ValidationDomainError("dosis_mg_por_kg debe ser numérica") from None
        if d <= 0 or frecuencia_horas <= 0 or duracion_dias <= 0:
            raise ValidationDomainError("Dosis, frecuencia y duración deben ser positivas")
        return cls(principio_activo=require_text(principio_activo, "principio_activo").lower(),
                   dosis_mg_por_kg=d, via=require_text(via, "via"), frecuencia_horas=frecuencia_horas,
                   duracion_dias=duracion_dias, dosis_calculada_mg=(d * peso.valor_kg).quantize(Decimal("0.01")))


@dataclass(frozen=True)
class ItemReceta:
    medicamento: MedicamentoDosificado
    justificacion: JustificacionClinica | None = None


@dataclass
class NotaSOAP:
    subjetivo: str = ""
    objetivo: str = ""
    analisis: str = ""
    plan: str = ""
    estado: EstadoNota = EstadoNota.BORRADOR
    firmada_por: CedulaProfesional | None = None
    firmada_en: datetime | None = None


@dataclass(frozen=True)
class NotaEnmienda:
    id: str
    cedula: CedulaProfesional
    motivo: str
    detalle: str
    fecha_hora: datetime


EXTENSIONES_LAB = (".pdf", ".png", ".jpg", ".jpeg")


@dataclass(frozen=True)
class ResultadoLaboratorio:
    """Documento analítico externo (p. ej. PDF de un hemograma) asociado a la consulta (US14)."""
    nombre_archivo: str
    sha256: str | None
    recibido_en: datetime

    def __post_init__(self) -> None:
        n = require_text(self.nombre_archivo, "nombre_archivo")
        if not n.lower().endswith(EXTENSIONES_LAB):
            raise ValidationDomainError(f"El resultado debe ser un archivo {', '.join(EXTENSIONES_LAB)}")
        if self.sha256 is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", self.sha256):
            raise ValidationDomainError("sha256 debe ser un hash hexadecimal de 64 caracteres")
        object.__setattr__(self, "nombre_archivo", n)


@dataclass
class EstudioLaboratorio:
    id: str
    tipo_estudio: str
    solicitado_en: datetime
    resultado: ResultadoLaboratorio | None = None

    @property
    def estado(self) -> str:
        return "RECIBIDO" if self.resultado else "PENDIENTE"


@dataclass
class Consulta(AggregateRoot):
    id: str
    paciente_id: str | None
    cedula: CedulaProfesional | None
    abierta_en: datetime
    triage: NivelTriage | None = None
    urgencia_descripcion: str | None = None
    nota: NotaSOAP = field(default_factory=NotaSOAP)
    receta: list[ItemReceta] = field(default_factory=list)
    enmiendas: list[NotaEnmienda] = field(default_factory=list)
    estudios: list[EstudioLaboratorio] = field(default_factory=list)

    # ---- fábricas
    @classmethod
    def abrir(cls, id: str, paciente_id: str, cedula: str, ahora: datetime) -> "Consulta":
        return cls(id=id, paciente_id=paciente_id, cedula=CedulaProfesional(cedula), abierta_en=ahora)

    @classmethod
    def admitir_urgencia(cls, id: str, descripcion_trauma: str, ahora: datetime,
                         paciente_id: str | None = None) -> "Consulta":
        """RN-02 / US03: pre-expediente temporal; no exige datos administrativos."""
        c = cls(id=id, paciente_id=paciente_id, cedula=None, abierta_en=ahora, triage=NivelTriage.ROJO,
                urgencia_descripcion=require_text(descripcion_trauma, "descripcion_trauma"))
        c._record(AdmisionUrgenciaActivadaEvent(consulta_id=id, descripcion=c.urgencia_descripcion))
        return c

    def paciente_requerido(self) -> str:
        """Id del paciente; una urgencia sin regularizar no puede prescribir ni solicitar estudios."""
        if not self.paciente_id:
            raise BusinessRuleViolation("La consulta de urgencia aún no tiene paciente asignado")
        return self.paciente_id

    def vincular_paciente(self, paciente_id: str) -> None:
        """Regularización administrativa posterior a la urgencia."""
        if self.paciente_id:
            raise BusinessRuleViolation("La consulta ya tiene paciente asignado")
        self.paciente_id = paciente_id

    # ---- RN-01
    @property
    def congelada(self) -> bool:
        return self.nota.estado is EstadoNota.CONGELADA

    def _asegurar_editable(self) -> None:
        if self.congelada:
            raise NotaInmutableError(
                "RN-01: la nota/receta está firmada y congelada; solo se admite una Nota de Enmienda")

    def redactar_soap(self, subjetivo: str, objetivo: str, analisis: str, plan: str) -> None:
        self._asegurar_editable()
        self.nota = replace(self.nota, subjetivo=subjetivo.strip(), objetivo=objetivo.strip(),
                            analisis=analisis.strip(), plan=plan.strip())

    def firmar_y_cerrar(self, cedula: str, ahora: datetime | None = None) -> None:
        self._asegurar_editable()
        n = self.nota
        if not all([n.subjetivo, n.objetivo, n.analisis, n.plan]):
            raise ValidationDomainError("La nota SOAP debe estar completa (S, O, A y P) antes de firmar")
        ced = CedulaProfesional(cedula)
        self.nota = replace(n, estado=EstadoNota.CONGELADA, firmada_por=ced, firmada_en=ahora or utcnow())
        self._record(NotaSOAPFirmadaEvent(consulta_id=self.id, cedula=ced.numero))

    def anexar_enmienda(self, cedula: str, motivo: str, detalle: str, ahora: datetime | None = None) -> NotaEnmienda:
        if not self.congelada:
            raise BusinessRuleViolation("Solo se anexan enmiendas a notas firmadas; la nota aún es editable")
        e = NotaEnmienda(id=new_id("ENM"), cedula=CedulaProfesional(cedula), motivo=require_text(motivo, "motivo"),
                         detalle=require_text(detalle, "detalle"), fecha_hora=ahora or utcnow())
        self.enmiendas.append(e)
        self._record(NotaEnmiendaAnexadaEvent(consulta_id=self.id, enmienda_id=e.id, cedula=e.cedula.numero))
        return e

    # ---- receta (la validación de alergias la orquesta ServicioValidacionAlergias, RN-04)
    def agregar_a_receta(self, med: MedicamentoDosificado, justificacion: JustificacionClinica | None = None) -> None:
        self._asegurar_editable()
        self.receta.append(ItemReceta(medicamento=med, justificacion=justificacion))
        if justificacion:
            self._record(PrescripcionConAlergiaJustificadaEvent(
                consulta_id=self.id, principio_activo=med.principio_activo, cedula=justificacion.cedula.numero))

    # ---- US14 laboratorio: anexos a la consulta; no editan la nota (RN-01 no se viola al adjuntar resultados)
    def solicitar_estudio(self, tipo_estudio: str, ahora: datetime | None = None) -> EstudioLaboratorio:
        if not self.paciente_id:
            raise BusinessRuleViolation("Regulariza la urgencia (asigna paciente) antes de solicitar estudios")
        e = EstudioLaboratorio(id=new_id("LAB"), tipo_estudio=require_text(tipo_estudio, "tipo_estudio"),
                               solicitado_en=ahora or utcnow())
        self.estudios.append(e)
        self._record(EstudioLaboratorioSolicitadoEvent(consulta_id=self.id, estudio_id=e.id, tipo_estudio=e.tipo_estudio))
        return e

    def adjuntar_resultado(self, estudio_id: str, nombre_archivo: str, sha256: str | None = None,
                           ahora: datetime | None = None) -> EstudioLaboratorio:
        e = next((x for x in self.estudios if x.id == estudio_id), None)
        if e is None:
            raise EntityNotFound(f"La consulta no tiene el estudio '{estudio_id}'")
        if e.resultado:
            raise BusinessRuleViolation("El estudio ya tiene un resultado adjunto; los resultados no se reemplazan")
        e.resultado = ResultadoLaboratorio(nombre_archivo, sha256, ahora or utcnow())
        self._record(ResultadoLaboratorioAdjuntadoEvent(
            consulta_id=self.id, estudio_id=e.id, paciente_id=self.paciente_id,
            cedula_medico=self.cedula.numero if self.cedula else None, tipo_estudio=e.tipo_estudio))
        return e
