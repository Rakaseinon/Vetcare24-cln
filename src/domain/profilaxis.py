"""ProfilaxisAggregate (raíz: RegistroVacuna). RN-03 trazabilidad y cálculo automático de refuerzo."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum

from .common import AggregateRoot, ValidationDomainError, require_text
from .events import (NotificacionRecordatorioDespachadaEvent, RefuerzoProfilacticoCalculadoEvent,
                     VacunaAplicadaEvent)


class EsquemaRefuerzo(str, Enum):
    CACHORRO_21 = "CACHORRO_21"   # quíntuple / triple felina: 21 días
    CACHORRO_28 = "CACHORRO_28"   # 28 días
    ANUAL = "ANUAL"               # rabia y refuerzos anuales: 365 días

    @property
    def dias(self) -> int:
        return {"CACHORRO_21": 21, "CACHORRO_28": 28, "ANUAL": 365}[self.value]


@dataclass(frozen=True)
class IntervaloRefuerzo:
    dias: int

    @staticmethod
    def para(edad_meses: int | None, esquema: EsquemaRefuerzo | None = None) -> "IntervaloRefuerzo":
        """Si no se indica esquema: < 12 meses -> 21 días; adultos o edad desconocida -> 365 días."""
        if esquema:
            return IntervaloRefuerzo(esquema.dias)
        if edad_meses is not None and edad_meses < 12:
            return IntervaloRefuerzo(EsquemaRefuerzo.CACHORRO_21.dias)
        return IntervaloRefuerzo(EsquemaRefuerzo.ANUAL.dias)


@dataclass(frozen=True)
class LoteBiologico:
    codigo: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "codigo", require_text(self.codigo, "lote (RN-03)").upper())


@dataclass(frozen=True)
class MarcaVacuna:
    nombre: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "nombre", require_text(self.nombre, "marca (RN-03)"))


@dataclass
class ProgramacionRefuerzo:
    fecha_programada: date
    intervalo_dias: int
    notificado: bool = False
    notificado_en: datetime | None = None


@dataclass
class RegistroVacuna(AggregateRoot):
    id: str
    paciente_id: str
    nombre_vacuna: str
    lote: LoteBiologico
    marca: MarcaVacuna
    fecha_aplicacion: date
    programacion: ProgramacionRefuerzo

    @classmethod
    def aplicar(cls, id: str, paciente_id: str, nombre_vacuna: str, lote: str | None, marca: str | None,
                fecha_aplicacion: date, hoy: date, intervalo: IntervaloRefuerzo) -> "RegistroVacuna":
        if fecha_aplicacion > hoy:
            raise ValidationDomainError("La fecha de aplicación no puede ser futura")
        r = cls(id=id, paciente_id=paciente_id, nombre_vacuna=require_text(nombre_vacuna, "nombre_vacuna"),
                lote=LoteBiologico(lote or ""), marca=MarcaVacuna(marca or ""), fecha_aplicacion=fecha_aplicacion,
                programacion=ProgramacionRefuerzo(fecha_aplicacion + timedelta(days=intervalo.dias), intervalo.dias))
        r._record(VacunaAplicadaEvent(registro_id=id, paciente_id=paciente_id, lote=r.lote.codigo))
        r._record(RefuerzoProfilacticoCalculadoEvent(registro_id=id, fecha_refuerzo=r.programacion.fecha_programada))
        return r

    def marcar_notificado(self, canal: str, ahora: datetime) -> None:
        self.programacion.notificado = True
        self.programacion.notificado_en = ahora
        self._record(NotificacionRecordatorioDespachadaEvent(registro_id=self.id, canal=canal))
