"""Esquemas Pydantic (contrato OpenAPI). Importes y pesos Decimal se serializan como cadena para no perder precisión."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------ entrada
class TutorIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'nombre': 'Ana López', 'identificacion_oficial': 'INE-ABC123456', 'telefono': '8112345678', 'email': 'ana@example.com', 'ciudad': 'Monterrey', 'canal_preferido': 'WHATSAPP'}]})

    nombre: str
    identificacion_oficial: str
    telefono: str | None = None
    email: str | None = None
    ciudad: str | None = None
    canal_preferido: Literal["WHATSAPP", "CORREO"] = "CORREO"


class MascotaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'tutor_id': 'PEGA-AQUI-EL-ID-DEL-TUTOR', 'nombre': 'Firulais', 'especie': 'PERRO', 'raza': 'Labrador', 'fecha_nacimiento': '2023-05-10', 'peso_kg': '12.5'}]})

    tutor_id: str
    nombre: str
    especie: str = Field(description="PERRO | GATO | OTRO")
    raza: str | None = None
    fecha_nacimiento: date | None = None
    peso_kg: Decimal | None = None
    microchip: str | None = None


class TriajeIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'peso_kg': '12.5', 'temperatura_c': '38.6', 'motivo': 'Vómito y decaimiento desde ayer', 'alergias': ['penicilina'], 'nivel': 'AMARILLO'}]})

    peso_kg: Decimal
    temperatura_c: Decimal
    motivo: str
    alergias: list[str] = []
    nivel: Literal["ROJO", "AMARILLO", "VERDE"] = "VERDE"


class AlergiaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'principio_activo': 'penicilina'}]})

    principio_activo: str


class TransferenciaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'nuevo_tutor_id': 'PEGA-AQUI-EL-ID-DEL-NUEVO-TUTOR'}]})

    nuevo_tutor_id: str


class UrgenciaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'descripcion_trauma': 'Atropellado, sangrado activo en extremidad posterior'}]})

    descripcion_trauma: str
    paciente_id: str | None = None


class ConsultaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'paciente_id': 'PEGA-AQUI-EL-ID-DE-LA-MASCOTA', 'cedula_veterinario': '1234567'}]})

    paciente_id: str
    cedula_veterinario: str


class NotaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'subjetivo': 'El tutor refiere vómito desde ayer.', 'objetivo': 'T 38.6 °C, mucosas rosadas, deshidratación leve.', 'analisis': 'Gastroenteritis aguda.', 'plan': 'Dieta blanda 48 h y control en 3 días.'}]})

    subjetivo: str
    objetivo: str
    analisis: str
    plan: str


class FirmaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'cedula': '1234567'}]})

    cedula: str


class EnmiendaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'cedula': '1234567', 'motivo': 'Corrección de peso', 'detalle': 'El peso correcto es 12.8 kg, no 12.5 kg.'}]})

    cedula: str
    motivo: str
    detalle: str


class RecetaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'principio_activo': 'penicilina', 'dosis_mg_por_kg': '10', 'via': 'oral', 'frecuencia_horas': 8, 'duracion_dias': 5}]})

    principio_activo: str
    dosis_mg_por_kg: Decimal
    via: str
    frecuencia_horas: int
    duracion_dias: int
    justificacion: str | None = Field(None, description="Justificación clínica para prescribir pese a una alergia (ADR-002)")
    cedula_justificante: str | None = None


class VacunaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'paciente_id': 'PEGA-AQUI-EL-ID-DE-LA-MASCOTA', 'nombre_vacuna': 'Quíntuple canina', 'lote': 'L-2026-0457', 'marca': 'Nobivac', 'esquema': 'CACHORRO_21'}]})

    paciente_id: str
    nombre_vacuna: str
    lote: str | None = None
    marca: str | None = None
    fecha_aplicacion: date | None = None
    esquema: Literal["CACHORRO_21", "CACHORRO_28", "ANUAL"] | None = None


class EstudioIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'tipo_estudio': 'Hemograma completo'}]})

    tipo_estudio: str = Field(description="p. ej. 'Hemograma completo', 'Perfil hematológico'")


class ResultadoLabIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'nombre_archivo': 'hemograma_firulais.pdf', 'sha256': '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08'}]})

    nombre_archivo: str = Field(description="Archivo remitido por el laboratorio (.pdf/.png/.jpg)")
    sha256: str | None = Field(None, description="Huella SHA-256 del archivo para integridad (opcional)")


class CitaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'paciente_id': 'PEGA-AQUI-EL-ID-DE-LA-MASCOTA', 'tipo': 'CONSULTA_GENERAL', 'inicio': '2026-12-07T10:00:00'}]})

    paciente_id: str
    tipo: Literal["VACUNA", "CONSULTA_GENERAL", "ESPECIALIDAD", "CIRUGIA"]
    inicio: datetime = Field(description="ISO 8601; sin zona horaria se interpreta como UTC")
    duracion_min: int | None = Field(None, description="Solo CIRUGIA: 90–120 min (por omisión 90)")


class HospitalizacionIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'paciente_id': 'PEGA-AQUI-EL-ID-DE-LA-MASCOTA', 'jaula_id': 'JP-01', 'plan_fluidoterapia': 'Suero Ringer 20 ml/h por 24 h', 'contagioso': False, 'critico': False}]})

    paciente_id: str
    jaula_id: str
    plan_fluidoterapia: str
    contagioso: bool = False
    critico: bool = False


class ConstantesIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'temperatura_c': '38.5', 'frecuencia_cardiaca': 100, 'frecuencia_respiratoria': 24, 'registrada_por': 'enfermera.lopez'}]})

    temperatura_c: Decimal
    frecuencia_cardiaca: int
    frecuencia_respiratoria: int
    registrada_por: str


class ConsumoIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'descripcion': 'Suero Ringer 500 ml', 'monto': '185.00'}]})

    descripcion: str
    monto: Decimal


class LineaIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"servicio_id": "VET-P001", "cantidad": 2}]})

    servicio_id: str
    cantidad: int


class OrdenIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'tutor_id': 'VET-C012', 'lineas': [{'servicio_id': 'VET-P001', 'cantidad': 2}], 'promocion_activa': False, 'autorizado': True}]})

    tutor_id: str
    lineas: list[LineaIn]
    promocion_activa: bool = False
    autorizado: bool = True
    referencia: str | None = None


class TransicionIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{'accion': 'aprobar'}]})

    accion: Literal["aprobar", "completar", "cancelar"]


# ------------------------------------------------------------------ salida
def _sin_propiedades_extra(schema: dict, _model: type) -> None:
    """Los modelos de salida admiten campos extra, pero Swagger no debe mostrar «additionalProp1»."""
    schema.pop("additionalProperties", None)


class _Out(BaseModel):
    model_config = ConfigDict(extra="allow", json_schema_extra=_sin_propiedades_extra)


def _con_ejemplo(ejemplo: dict) -> ConfigDict:
    """Modelo de salida con un ejemplo realista (en lugar de «string») y sin «additionalProp1»."""
    def completar(schema: dict, _model: type) -> None:
        schema.pop("additionalProperties", None)
        schema["examples"] = [ejemplo]
    return ConfigDict(extra="allow", json_schema_extra=completar)


class TutorOut(_Out):
    model_config = _con_ejemplo({'id': 'TUT-3f9a1c2b7d10', 'nombre': 'Ana López', 'activo': True, 'es_preferente': False, 'canal_preferido': 'WHATSAPP'})

    id: str
    nombre: str
    activo: bool
    es_preferente: bool
    canal_preferido: str


class PacienteOut(_Out):
    model_config = _con_ejemplo({'id': 'PAC-8e41b0c5a9d2', 'codigo_expediente': 'EXP-2026-0001', 'nombre': 'Firulais', 'especie': 'PERRO', 'tutor_id': 'TUT-3f9a1c2b7d10', 'peso_kg': '12.5', 'microchip': None, 'alerta_alergia': True, 'alergias': ['penicilina']})

    id: str
    codigo_expediente: str
    nombre: str
    especie: str
    tutor_id: str
    peso_kg: Decimal | None
    microchip: str | None
    alerta_alergia: bool
    alergias: list[str]


class CitaOut(_Out):
    model_config = _con_ejemplo({'id': 'CIT-5b2d7e90c1f4', 'paciente_id': 'PAC-8e41b0c5a9d2', 'tipo': 'CONSULTA_GENERAL', 'sala': 'CONSULTORIO', 'inicio': '2026-12-07T10:00:00', 'fin': '2026-12-07T10:30:00', 'duracion_min': 30, 'estado': 'SOLICITADA', 'cancelacion_tardia': False, 'acciones_permitidas': ['confirmar', 'cancelar']})

    id: str
    paciente_id: str
    tipo: str
    sala: str
    inicio: datetime
    fin: datetime
    duracion_min: int
    estado: str
    cancelacion_tardia: bool
    acciones_permitidas: list[str]


class ConsultaOut(_Out):
    model_config = _con_ejemplo({'id': 'CON-a7c3e19d4b62', 'paciente_id': 'PAC-8e41b0c5a9d2', 'triage': None, 'nota': {'firmada': False}, 'receta': [], 'enmiendas': []})

    id: str
    paciente_id: str | None
    triage: str | None
    nota: dict[str, Any]
    receta: list[dict[str, Any]]
    enmiendas: list[dict[str, Any]]


class VacunaOut(_Out):
    model_config = _con_ejemplo({'id': 'VAC-1d6f8a30e5b7', 'paciente_id': 'PAC-8e41b0c5a9d2', 'nombre_vacuna': 'Quíntuple canina', 'lote': 'L-2026-0457', 'marca': 'Nobivac', 'fecha_aplicacion': '2026-11-06', 'fecha_refuerzo': '2026-11-27', 'intervalo_dias': 21})

    id: str
    paciente_id: str
    nombre_vacuna: str
    lote: str
    marca: str
    fecha_aplicacion: date
    fecha_refuerzo: date
    intervalo_dias: int


class JaulaOut(_Out):
    model_config = _con_ejemplo({'id': 'JP-01', 'tipo': 'PERRO', 'libre': True})

    id: str
    tipo: str
    libre: bool


class HospitalizacionOut(_Out):
    model_config = _con_ejemplo({'id': 'HOS-c04e92b7a1d8', 'paciente_id': 'PAC-8e41b0c5a9d2', 'jaula_id': 'JP-01', 'estado': 'HOSPITALIZADO', 'criticidad': 'ESTABLE', 'alta_medica_firmada': False, 'cuenta_liquidada': False, 'apto_para_egreso': False, 'precuenta_total': '185.00', 'bitacora': []})

    id: str
    paciente_id: str
    jaula_id: str
    estado: str
    criticidad: str
    alta_medica_firmada: bool
    cuenta_liquidada: bool
    apto_para_egreso: bool
    precuenta_total: Decimal
    bitacora: list[dict[str, Any]]


class AltaOut(BaseModel):
    resultado: Literal["EGRESO_CONCLUIDO", "PENDIENTE_VALIDACION_CRUZADA"]
    hospitalizacion: HospitalizacionOut


class ServicioOut(_Out):
    model_config = _con_ejemplo({'id': 'VET-P001', 'descripcion': 'Consulta 01', 'precio': '313.00', 'capacidad': 10, 'habilitado': True})

    id: str
    descripcion: str
    precio: Decimal
    capacidad: int
    habilitado: bool


class OrdenOut(_Out):
    model_config = _con_ejemplo({'id': 'VET-O001', 'tutor_id': 'VET-C012', 'estado': 'SOLICITADA', 'total': '7587.00', 'puede_procesarse': True, 'motivos_no_procesable': [], 'elegible_beneficio_referencia': False, 'acciones_permitidas': ['aprobar', 'cancelar'], 'lineas': []})

    id: str
    tutor_id: str
    estado: str
    total: Decimal
    puede_procesarse: bool
    motivos_no_procesable: list[str]
    elegible_beneficio_referencia: bool
    acciones_permitidas: list[str]
    lineas: list[dict[str, Any]]


class ReporteOut(_Out):
    model_config = _con_ejemplo({'desde': '2026-10-30', 'hasta': '2026-11-06', 'tasa_ocupacion': 0.15, 'vacunas_aplicadas': 3, 'ordenes_canceladas': 0, 'citas_canceladas': 1, 'citas_canceladas_tardias': 0})

    desde: date
    hasta: date
    tasa_ocupacion: float
    vacunas_aplicadas: int
    ordenes_canceladas: int
    citas_canceladas: int
    citas_canceladas_tardias: int


class ErrorOut(BaseModel):
    codigo: str = Field(description="Tipo de error de negocio, p. ej. AlergiaBloqueoError, NotaInmutableError, InvalidStateTransition")
    mensaje: str = Field(description="Explicación legible del motivo")
