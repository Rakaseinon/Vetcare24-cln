"""Adaptador de notificaciones (WhatsApp/correo). Simulado: registra el envío (integrar proveedor está fuera de alcance)."""
from __future__ import annotations

import logging

log = logging.getLogger("vetcare.notificaciones")


class LogNotificador:
    def __init__(self) -> None:
        self.enviados: list[tuple[str, str, str]] = []

    def enviar(self, canal: str, destino: str, mensaje: str) -> None:
        self.enviados.append((canal, destino, mensaje))
        log.info("[%s] -> %s: %s", canal, destino, mensaje)
