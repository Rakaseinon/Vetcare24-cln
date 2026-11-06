"""Tutor / propietario: titular legal y responsable financiero (glosario #1)."""
from __future__ import annotations

from dataclasses import dataclass

from .common import AggregateRoot, BusinessRuleViolation, ValidationDomainError, require_text

CANALES = {"WHATSAPP", "CORREO"}


@dataclass
class Tutor(AggregateRoot):
    id: str
    nombre: str
    activo: bool = True
    es_preferente: bool = False
    identificacion_oficial: str | None = None
    telefono: str | None = None
    email: str | None = None
    ciudad: str | None = None
    canal_preferido: str = "CORREO"

    @classmethod
    def registrar(cls, id: str, nombre: str, identificacion_oficial: str, telefono: str | None = None,
                  email: str | None = None, ciudad: str | None = None,
                  canal_preferido: str = "CORREO") -> "Tutor":
        """US01: datos válidos del propietario (nombre, identificación oficial y un medio de contacto)."""
        if not (telefono or email):
            raise ValidationDomainError("Se requiere al menos teléfono o correo de contacto")
        canal = canal_preferido.upper()
        if canal not in CANALES:
            raise ValidationDomainError(f"canal_preferido debe ser uno de {sorted(CANALES)}")
        return cls(id=id, nombre=require_text(nombre, "nombre"),
                   identificacion_oficial=require_text(identificacion_oficial, "identificacion_oficial"),
                   telefono=telefono, email=email, ciudad=ciudad, canal_preferido=canal)

    def asegurar_activo(self, para: str) -> None:
        """Un tutor inactivo no puede asumir nuevas responsabilidades (mascotas, titularidad)."""
        if not self.activo:
            raise BusinessRuleViolation(f"El tutor '{self.id}' está inactivo; no puede {para}")
