"""Ejecuta casos_prueba.csv y transiciones_prueba.csv del paquete VetCare 24 contra el dominio real.

Genera data/resultados/casos_prueba_resultado.csv y transiciones_prueba_resultado.csv con la columna
`resultado_alumno` rellenada. Uso:  python scripts/ejecutar_casos_prueba.py [data_dir] [out_dir]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.common import DomainError  # noqa: E402
from src.infrastructure.config import Settings  # noqa: E402
from src.infrastructure.db import create_schema, make_engine, make_session_factory  # noqa: E402
from src.infrastructure.event_bus import InMemoryEventBus  # noqa: E402
from src.infrastructure.seed import sembrar_paquete_datos  # noqa: E402
from src.infrastructure.uow import SqlAlchemyUnitOfWork  # noqa: E402


def leer(p: Path) -> tuple[list[str], list[dict]]:
    with p.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), list(r)


def escribir(p: Path, cols: list[str], rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def ejecutar(data_dir: Path, out_dir: Path) -> dict[str, int]:
    engine = make_engine("sqlite://")
    create_schema(engine)
    bus = InMemoryEventBus()
    sf = make_session_factory(engine)
    uow_factory = lambda: SqlAlchemyUnitOfWork(sf, bus)  # noqa: E731
    sembrar_paquete_datos(uow_factory, data_dir)

    cols, casos = leer(data_dir / "casos_prueba.csv")
    for c in casos:
        with uow_factory() as uow:
            o = uow.ordenes.get(c["operacion_id"])
            t = uow.tutores.get(o.tutor_id)
            if c["tipo_prueba"] == "validar_operacion":
                ok = o.puede_procesarse(t)
                c["resultado_alumno"] = "VALIDA" if ok else "INVALIDA: " + ", ".join(o.motivos_no_procesable(t))
            else:
                c["resultado_alumno"] = "APLICA" if o.elegible_beneficio_referencia(t) else "NO_APLICA"
    escribir(out_dir / "casos_prueba_resultado.csv", cols, casos)

    cols_t, trans = leer(data_dir / "transiciones_prueba.csv")
    for tr in trans:
        with uow_factory() as uow:
            o = uow.ordenes.get(tr["operacion_id"])
            t = uow.tutores.get(o.tutor_id)
            accion = tr["accion_sugerida"]
            antes = o.estado.value
            try:
                if accion == "repetir_aprobacion":
                    o.aprobar(t)
                    o.aprobar(t)
                elif accion == "saltar_estado":
                    o.completar()  # SOLICITADA -> REALIZADA sin confirmar: no permitido
                else:
                    {"aprobar": lambda: o.aprobar(t), "completar": o.completar, "cancelar": o.cancelar}[accion]()
                evs = ",".join(e.name for e in o.pull_events())
                tr["resultado_alumno"] = f"OK: {antes}->{o.estado.value} [{evs}]"
            except DomainError as e:
                tr["resultado_alumno"] = f"RECHAZADA ({type(e).__name__}): {e}"
    escribir(out_dir / "transiciones_prueba_resultado.csv", cols_t, trans)
    engine.dispose()
    return {"casos": len(casos), "transiciones": len(trans)}


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data"
    o = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "resultados"
    print(ejecutar(d, o))
