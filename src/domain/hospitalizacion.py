"""HospitalizacionAggregate (raíz: Hospitalizacion) + Jaula. RN-06 validación cruzada de alta.

Máquina de estados:
  HOSPITALIZADO --(FIRMAR_ALTA | LIQUIDAR_CUENTA)--> PENDIENTE_VALIDACION_CRUZADA
  PENDIENTE_VALIDACION_CRUZADA --EGRESAR [alta firmada AND cuenta liquidada]--> EGRESADO
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

from .common import (AggregateRoot, BusinessRuleViolation, StateMachine, ValidationDomainError,
                     require_text, utcnow)
from .consulta import CedulaProfesional
from .events import (AltaMedicaAutorizadaEvent, CuentaLiquidadaEvent, JaulaLiberadaEvent,
                     PacienteHospitalizadoEvent, SignosVitalesFueraDeRangoEvent)
from .specifications import LecturaVencidaSpec, apto_para_egreso

VENTANA_ESTABLE = timedelta(hours=4)   # BRD / entrevista: al menos cada 4 horas
VENTANA_CRITICO = timedelta(hours=2)   # ADR-001: 2 horas en estado crítico

# Rangos de referencia (supuesto técnico a validar con el Director Médico; ver README).
RANGO_TEMPERATURA_C = (Decimal("37.5"), Decimal("39.5"))
RANGO_FREC_CARDIACA = (60, 180)
RANGO_FREC_RESPIRATORIA = (10, 40)


class EstadoHospitalizacion(str, Enum):
    HOSPITALIZADO = "HOSPITALIZADO"
    PENDIENTE_VALIDACION_CRUZADA = "PENDIENTE_VALIDACION_CRUZADA"
    EGRESADO = "EGRESADO"


class Criticidad(str, Enum):
    ESTABLE = "ESTABLE"
    CRITICO = "CRITICO"


class TipoJaula(str, Enum):
    PERRO = "PERRO"
    GATO = "GATO"
    AISLAMIENTO = "AISLAMIENTO"


_H = EstadoHospitalizacion
MAQUINA_HOSPITALIZACION: StateMachine[EstadoHospitalizacion] = StateMachine("Hospitalizacion", [
    (_H.HOSPITALIZADO, "FIRMAR_ALTA", _H.PENDIENTE_VALIDACION_CRUZADA),
    (_H.HOSPITALIZADO, "LIQUIDAR_CUENTA", _H.PENDIENTE_VALIDACION_CRUZADA),
    (_H.PENDIENTE_VALIDACION_CRUZADA, "FIRMAR_ALTA", _H.PENDIENTE_VALIDACION_CRUZADA),
    (_H.PENDIENTE_VALIDACION_CRUZADA, "LIQUIDAR_CUENTA", _H.PENDIENTE_VALIDACION_CRUZADA),
    (_H.PENDIENTE_VALIDACION_CRUZADA, "EGRESAR", _H.EGRESADO),
])


@dataclass(frozen=True)
class ConstantesVitales:
    temperatura_c: Decimal
    frecuencia_cardiaca: int
    frecuencia_respiratoria: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "temperatura_c", Decimal(str(self.temperatura_c)))
        if self.frecuencia_cardiaca <= 0 or self.frecuencia_respiratoria <= 0 or self.temperatura_c <= 0:
            raise ValidationDomainError("Las constantes vitales deben ser positivas")

    def alertas(self) -> list[str]:
        out = []
        if not (RANGO_TEMPERATURA_C[0] <= self.temperatura_c <= RANGO_TEMPERATURA_C[1]):
            out.append(f"temperatura {self.temperatura_c} °C fuera de rango")
        if not (RANGO_FREC_CARDIACA[0] <= self.frecuencia_cardiaca <= RANGO_FREC_CARDIACA[1]):
            out.append(f"frecuencia cardíaca {self.frecuencia_cardiaca} fuera de rango")
        if not (RANGO_FREC_RESPIRATORIA[0] <= self.frecuencia_respiratoria <= RANGO_FREC_RESPIRATORIA[1]):
            out.append(f"frecuencia respiratoria {self.frecuencia_respiratoria} fuera de rango")
        return out


@dataclass(frozen=True)
class LecturaBitacora:
    registrada_en: datetime
    registrada_por: str
    constantes: ConstantesVitales
    alertas: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsumoPrecuenta:
    descripcion: str
    monto: Decimal


@dataclass
class Jaula(AggregateRoot):
    id: str
    tipo: TipoJaula
    hospitalizacion_id: str | None = None

    @property
    def libre(self) -> bool:
        return self.hospitalizacion_id is None

    def ocupar(self, hospitalizacion_id: str) -> None:
        if not self.libre:
            raise BusinessRuleViolation(f"La jaula {self.id} ya está ocupada")
        self.hospitalizacion_id = hospitalizacion_id

    def liberar(self) -> None:
        hid, self.hospitalizacion_id = self.hospitalizacion_id, None
        self._record(JaulaLiberadaEvent(jaula_id=self.id, hospitalizacion_id=hid or ""))


@dataclass
class Hospitalizacion(AggregateRoot):
    id: str
    paciente_id: str
    jaula_id: str
    plan_fluidoterapia: str
    ingreso: datetime
    estado: EstadoHospitalizacion = EstadoHospitalizacion.HOSPITALIZADO
    criticidad: Criticidad = Criticidad.ESTABLE
    alta_medica_firmada: bool = False
    alta_medica_cedula: CedulaProfesional | None = None
    cuenta_liquidada: bool = False
    egreso_en: datetime | None = None
    bitacora: list[LecturaBitacora] = field(default_factory=list)
    consumos: list[ConsumoPrecuenta] = field(default_factory=list)

    @classmethod
    def ingresar(cls, id: str, paciente_id: str, jaula_id: str, plan_fluidoterapia: str, ahora: datetime,
                 critico: bool = False) -> "Hospitalizacion":
        h = cls(id=id, paciente_id=paciente_id, jaula_id=jaula_id,
                plan_fluidoterapia=require_text(plan_fluidoterapia, "plan_fluidoterapia"), ingreso=ahora,
                criticidad=Criticidad.CRITICO if critico else Criticidad.ESTABLE)
        h._record(PacienteHospitalizadoEvent(hospitalizacion_id=id, paciente_id=paciente_id, jaula_id=jaula_id))
        return h

    # ---- bitácora (RF-06, US10)
    def _asegurar_activa(self) -> None:
        if self.estado is EstadoHospitalizacion.EGRESADO:
            raise BusinessRuleViolation("La hospitalización ya concluyó")

    def ventana_maxima(self) -> timedelta:
        return VENTANA_CRITICO if self.criticidad is Criticidad.CRITICO else VENTANA_ESTABLE

    def ultima_referencia(self) -> datetime:
        return self.bitacora[-1].registrada_en if self.bitacora else self.ingreso

    def lectura_vencida(self, ahora: datetime) -> bool:
        return LecturaVencidaSpec(ahora).is_satisfied_by(self)

    def registrar_constantes(self, constantes: ConstantesVitales, registrada_por: str,
                             ahora: datetime | None = None) -> list[str]:
        self._asegurar_activa()
        alertas = constantes.alertas()
        self.bitacora.append(LecturaBitacora(ahora or utcnow(), require_text(registrada_por, "registrada_por"),
                                             constantes, tuple(alertas)))
        # Supuesto: una lectura fuera de rango eleva a CRITICO (ventana de 2 h) hasta una lectura normal.
        self.criticidad = Criticidad.CRITICO if alertas else Criticidad.ESTABLE
        if alertas:
            self._record(SignosVitalesFueraDeRangoEvent(hospitalizacion_id=self.id, alertas=tuple(alertas)))
        return alertas

    def agregar_consumo(self, descripcion: str, monto: Decimal | float | str) -> None:
        self._asegurar_activa()
        m = Decimal(str(monto))
        if m <= 0:
            raise ValidationDomainError("El monto del consumo debe ser positivo")
        self.consumos.append(ConsumoPrecuenta(require_text(descripcion, "descripcion"), m))

    @property
    def precuenta_total(self) -> Decimal:
        return sum((c.monto for c in self.consumos), Decimal("0")).quantize(Decimal("0.01"))

    # ---- RN-06
    def es_apto_para_egreso(self) -> bool:
        return apto_para_egreso().is_satisfied_by(self)

    def firmar_alta_medica(self, cedula: str) -> None:
        self._asegurar_activa()
        if self.alta_medica_firmada:
            raise BusinessRuleViolation("El alta médica ya fue firmada")
        ced = CedulaProfesional(cedula)
        self.estado = MAQUINA_HOSPITALIZACION.fire(self.estado, "FIRMAR_ALTA")
        self.alta_medica_firmada, self.alta_medica_cedula = True, ced
        self._record(AltaMedicaAutorizadaEvent(hospitalizacion_id=self.id, cedula=ced.numero))

    def liquidar_cuenta(self) -> None:
        self._asegurar_activa()
        if self.cuenta_liquidada:
            raise BusinessRuleViolation("La cuenta ya fue liquidada")
        self.estado = MAQUINA_HOSPITALIZACION.fire(self.estado, "LIQUIDAR_CUENTA")
        self.cuenta_liquidada = True
        self._record(CuentaLiquidadaEvent(hospitalizacion_id=self.id))

    def intentar_egreso(self, ahora: datetime | None = None) -> bool:
        """Devuelve True si el paciente egresa; False si sigue PendienteValidacionCruzada."""
        if self.estado is not EstadoHospitalizacion.PENDIENTE_VALIDACION_CRUZADA or not self.es_apto_para_egreso():
            return False
        self.estado = MAQUINA_HOSPITALIZACION.fire(self.estado, "EGRESAR")
        self.egreso_en = ahora or utcnow()
        return True
