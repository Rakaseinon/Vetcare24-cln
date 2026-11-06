"""RBAC simplificado (RNF-03). Rol por encabezado X-Rol — DEMO: en producción se sustituye por JWT/OIDC."""
from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

ROLES = ("RECEPCION", "VETERINARIO", "ENFERMERIA", "DIRECTOR")
TODOS = ROLES
CLINICOS = ("VETERINARIO", "DIRECTOR")

_header = APIKeyHeader(name="X-Rol", scheme_name="X-Rol", auto_error=False,
                       description="Rol del usuario (demostración, ADR-004): RECEPCION, VETERINARIO, ENFERMERIA o "
                                   "DIRECTOR. DIRECTOR puede usar todos los recursos; prueba otro rol para ver el 403 de RNF-03.")


def requiere(*permitidos: str):
    def dependencia(rol: str | None = Security(_header)) -> str:
        if not rol:
            raise HTTPException(401, "Falta el encabezado X-Rol")
        r = rol.strip().upper()
        if r not in ROLES:
            raise HTTPException(401, f"Rol desconocido: {rol}")
        if r not in permitidos:
            raise HTTPException(403, f"RNF-03: el rol {r} no tiene acceso a este recurso")
        return r
    dependencia.roles = tuple(permitidos)  # lo usa api/docs.py para documentar los roles de cada recurso
    return dependencia
