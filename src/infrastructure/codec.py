"""Codec JSON de agregados: dataclasses/Enum/Decimal/fechas <-> documento JSON con etiquetas de tipo.

Permite persistir cada agregado como una unidad (ADR-003) sin ensuciar el dominio con mapeos ORM.
"""
from __future__ import annotations

import dataclasses
import importlib
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

_MODULOS = ["common", "events", "specifications", "tutor", "paciente", "consulta", "hospitalizacion",
            "profilaxis", "orden_servicio", "agenda"]
_REGISTRO: dict[str, type] = {}


def _registrar() -> None:
    if _REGISTRO:
        return
    for m in _MODULOS:
        mod = importlib.import_module(f"src.domain.{m}")
        for nombre, obj in vars(mod).items():
            if isinstance(obj, type) and obj.__module__ == mod.__name__ and (
                    dataclasses.is_dataclass(obj) or issubclass(obj, Enum)):
                _REGISTRO[nombre] = obj


def encode(o: Any) -> Any:
    if isinstance(o, Enum):  # antes que str: los Enum del dominio heredan de str
        return {"__enum": type(o).__name__, "v": o.value}
    if o is None or isinstance(o, (bool, int, float, str)):
        return o
    if isinstance(o, Decimal):
        return {"__dec": str(o)}
    if isinstance(o, datetime):  # antes que date: datetime hereda de date
        return {"__dt": o.isoformat()}
    if isinstance(o, date):
        return {"__d": o.isoformat()}
    if isinstance(o, tuple):
        return {"__tuple": [encode(x) for x in o]}
    if isinstance(o, list):
        return [encode(x) for x in o]
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {"__t": type(o).__name__, "f": {f.name: encode(getattr(o, f.name)) for f in dataclasses.fields(o)}}
    raise TypeError(f"No serializable: {type(o)!r}")


def decode(d: Any) -> Any:
    _registrar()
    if isinstance(d, list):
        return [decode(x) for x in d]
    if not isinstance(d, dict):
        return d
    if "__enum" in d:
        return _REGISTRO[d["__enum"]](d["v"])
    if "__dec" in d:
        return Decimal(d["__dec"])
    if "__dt" in d:
        return datetime.fromisoformat(d["__dt"])
    if "__d" in d:
        return date.fromisoformat(d["__d"])
    if "__tuple" in d:
        return tuple(decode(x) for x in d["__tuple"])
    if "__t" in d:
        return _REGISTRO[d["__t"]](**{k: decode(v) for k, v in d["f"].items()})
    raise ValueError(f"Documento no reconocido: {d!r}")
