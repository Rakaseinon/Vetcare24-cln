"""PacienteAggregate (raíz: Paciente). Invariantes: microchip único (en repositorio), RN-05."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

from .common import AggregateRoot, BusinessRuleViolation, ValidationDomainError, require_text
from .events import AlergiaDetectadaEvent, PacienteRegistradoEvent, TutorReasignadoEvent

ESPECIES = {"PERRO", "GATO", "OTRO"}


class NivelTriage(str, Enum):
    """Semáforo de triaje veterinario (glosario #4)."""

    ROJO = "ROJO"
    AMARILLO = "AMARILLO"
    VERDE = "VERDE"


@dataclass(frozen=True)
class MicrochipCode:
    codigo: str

    def __post_init__(self) -> None:
        c = str(self.codigo).strip()
        if not re.fullmatch(r"[0-9A-Za-z]{9,15}", c):
            raise ValidationDomainError("El microchip debe tener entre 9 y 15 caracteres alfanuméricos")
        object.__setattr__(self, "codigo", c.upper())


@dataclass(frozen=True)
class Peso:
    valor_kg: Decimal

    def __post_init__(self) -> None:
        try:
            v = Decimal(str(self.valor_kg))
        except InvalidOperation:
            raise ValidationDomainError("El peso debe ser numérico") from None
        if not (Decimal("0") < v <= Decimal("200")):
            raise ValidationDomainError("El peso debe estar entre 0 y 200 kg")
        object.__setattr__(self, "valor_kg", v)


@dataclass(frozen=True)
class Alergeno:
    principio_activo: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "principio_activo", require_text(self.principio_activo, "principio_activo").lower())


@dataclass
class TutorResponsable:
    """Entidad interna: periodo de titularidad legal del paciente (RN-05)."""

    tutor_id: str
    desde: date
    hasta: date | None = None


@dataclass(frozen=True)
class HojaTriaje:
    """RF-02: peso (indispensable para dosificar), temperatura y motivo al llegar."""

    registrada_en: datetime
    peso: Peso
    temperatura_c: Decimal
    motivo: str
    nivel: NivelTriage = NivelTriage.VERDE


@dataclass
class Paciente(AggregateRoot):
    id: str
    nombre: str
    especie: str
    tutor_id: str
    codigo_expediente: str
    raza: str | None = None
    fecha_nacimiento: date | None = None
    peso: Peso | None = None
    microchip: MicrochipCode | None = None
    alergenos: list[Alergeno] = field(default_factory=list)
    titularidad: list[TutorResponsable] = field(default_factory=list)
    triajes: list[HojaTriaje] = field(default_factory=list)

    @classmethod
    def registrar(cls, id: str, nombre: str, especie: str, tutor_id: str, codigo_expediente: str,
                  hoy: date, raza: str | None = None, fecha_nacimiento: date | None = None,
                  peso_kg: Decimal | float | str | None = None, microchip: str | None = None) -> "Paciente":
        esp = require_text(especie, "especie").upper()
        if esp not in ESPECIES:
            raise ValidationDomainError(f"especie debe ser una de {sorted(ESPECIES)}")
        if fecha_nacimiento and fecha_nacimiento > hoy:
            raise ValidationDomainError("La fecha de nacimiento no puede ser futura")
        p = cls(id=id, nombre=require_text(nombre, "nombre"), especie=esp, tutor_id=tutor_id,
                codigo_expediente=codigo_expediente, raza=raza, fecha_nacimiento=fecha_nacimiento,
                peso=Peso(peso_kg) if peso_kg is not None else None,
                microchip=MicrochipCode(microchip) if microchip else None,
                titularidad=[TutorResponsable(tutor_id=tutor_id, desde=hoy)])
        p._record(PacienteRegistradoEvent(paciente_id=id, tutor_id=tutor_id))
        return p

    def edad_meses(self, hoy: date) -> int | None:
        if not self.fecha_nacimiento:
            return None
        n = self.fecha_nacimiento
        return (hoy.year - n.year) * 12 + (hoy.month - n.month) - (1 if hoy.day < n.day else 0)

    def actualizar_peso(self, peso: Peso) -> None:
        self.peso = peso

    def registrar_triaje(self, ahora: datetime, peso: Peso, temperatura_c: Decimal | float | str, motivo: str,
                         alergias: list[str] | None = None, nivel: NivelTriage = NivelTriage.VERDE) -> HojaTriaje:
        """US04: actualiza peso y alérgenos del perfil y deja la hoja de triaje en el expediente."""
        try:
            temp = Decimal(str(temperatura_c))
        except InvalidOperation:
            raise ValidationDomainError("La temperatura debe ser numérica") from None
        if not (Decimal("30") <= temp <= Decimal("45")):
            raise ValidationDomainError("La temperatura debe estar entre 30 y 45 °C")
        self.actualizar_peso(peso)
        for a in alergias or []:
            self.registrar_alergia(Alergeno(a))
        hoja = HojaTriaje(ahora, peso, temp, require_text(motivo, "motivo"), nivel)
        self.triajes.append(hoja)
        return hoja

    def registrar_alergia(self, alergeno: Alergeno) -> bool:
        """Devuelve True si es una alergia nueva (US04: alerta permanente en el encabezado)."""
        if alergeno in self.alergenos:
            return False
        self.alergenos.append(alergeno)
        self._record(AlergiaDetectadaEvent(paciente_id=self.id, principio_activo=alergeno.principio_activo))
        return True

    def tiene_alergia_a(self, principio_activo: str) -> bool:
        return principio_activo.strip().lower() in {a.principio_activo for a in self.alergenos}

    @property
    def alerta_alergia(self) -> bool:
        return bool(self.alergenos)

    def transferir_a(self, nuevo_tutor_id: str, hoy: date) -> None:
        """RN-05: cambia la titularidad; el historial clínico (otros agregados, por paciente_id) no se toca."""
        if nuevo_tutor_id == self.tutor_id:
            raise BusinessRuleViolation("El paciente ya pertenece a ese tutor")
        for t in self.titularidad:
            if t.hasta is None:
                t.hasta = hoy
        self.titularidad.append(TutorResponsable(tutor_id=nuevo_tutor_id, desde=hoy))
        anterior, self.tutor_id = self.tutor_id, nuevo_tutor_id
        self._record(TutorReasignadoEvent(paciente_id=self.id, tutor_anterior=anterior, tutor_nuevo=nuevo_tutor_id))
