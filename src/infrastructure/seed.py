"""Carga de datos iniciales: paquete de pruebas VetCare 24 (CSV) + jaulas de la clínica (12 perro, 6 gato, 2 aislamiento)."""
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from ..domain.hospitalizacion import Jaula, TipoJaula
from ..domain.orden_servicio import EstadoOrden, LineaOrden, OrdenServicio, ServicioCatalogo
from ..domain.tutor import Tutor

CAPACIDAD_JAULAS = [(TipoJaula.PERRO, 12, "JP"), (TipoJaula.GATO, 6, "JG"), (TipoJaula.AISLAMIENTO, 2, "JA")]


def _leer(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sembrar_jaulas(uow_factory) -> int:
    with uow_factory() as uow:
        if uow.jaulas.count():
            return 0
        n = 0
        for tipo, cantidad, pref in CAPACIDAD_JAULAS:
            for i in range(1, cantidad + 1):
                uow.jaulas.save(Jaula(id=f"{pref}-{i:02d}", tipo=tipo))
                n += 1
        uow.commit()
        return n


def sembrar_paquete_datos(uow_factory, data_dir: Path) -> dict[str, int]:
    """Importa actores, catálogo, operaciones y detalle. Las operaciones arrancan en su estado_inicial."""
    with uow_factory() as uow:
        if uow.servicios.count():  # el catálogo solo existe si el paquete ya se cargó (idempotente)
            return {"tutores": 0, "servicios": 0, "ordenes": 0}
        for r in _leer(data_dir / "actores.csv"):
            uow.tutores.save(Tutor(id=r["actor_id"], nombre=r["nombre"], ciudad=r["ciudad"],
                                   activo=r["activo"] == "1", es_preferente=r["es_preferente"] == "1"))
        catalogo = {}
        for r in _leer(data_dir / "catalogo.csv"):
            s = ServicioCatalogo(id=r["recurso_id"], descripcion=r["descripcion"], precio=Decimal(r["precio_mxn"]),
                                 capacidad=int(r["capacidad_o_stock"]), habilitado=r["habilitado"] == "1")
            catalogo[s.id] = s
            uow.servicios.save(s)
        lineas: dict[str, list[LineaOrden]] = {}
        for r in _leer(data_dir / "detalle_operaciones.csv"):
            s = catalogo[r["recurso_id"]]
            lineas.setdefault(r["operacion_id"], []).append(LineaOrden(s.id, s.descripcion, s.precio, int(r["cantidad"])))
        n = 0
        for r in _leer(data_dir / "operaciones.csv"):
            uow.ordenes.save(OrdenServicio(
                id=r["operacion_id"], tutor_id=r["actor_id"], fecha_solicitud=date.fromisoformat(r["fecha_solicitud"]),
                estado=EstadoOrden(r["estado_inicial"]), promocion_activa=r["promocion_activa"] == "1",
                autorizado=r["autorizado"] == "1", referencia=r["referencia"], lineas=lineas.get(r["operacion_id"], [])))
            n += 1
        uow.commit()
        return {"tutores": uow.tutores.count(), "servicios": len(catalogo), "ordenes": n}
