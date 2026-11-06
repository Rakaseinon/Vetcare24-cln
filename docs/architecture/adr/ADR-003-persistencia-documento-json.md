# ADR-003 — Persistencia: un agregado = una fila (columnas indexadas + documento JSON)

- **Estatus:** Aceptado · **Fecha:** 2026-11-01

## Contexto
ADR-001 exige aislar el dominio del ORM. Mapear cada entidad interna (notas, enmiendas, bitácora, receta…) a tablas relacionales
filtraría estructura de BD al dominio y complicaría las invariantes (se guarda el agregado completo o nada).

## Decisión
Cada raíz se guarda en **una fila**: columnas planas para consultar/indexar + `doc` con el agregado completo (`JSON`, y `JSONB` en PostgreSQL vía `with_variant`).
`infrastructure/codec.py` serializa dataclasses/Enum/Decimal/fechas con etiquetas de tipo; el dominio no conoce SQLAlchemy.

## Alternativas descartadas
ORM clásico con tablas hijas (más fricción, riesgo de guardar agregados a medias); event sourcing (excesivo para el alcance).

## Consecuencias
(+) Atomicidad natural por agregado, dominio puro, SQLite en pruebas y PostgreSQL en producción con el mismo código (ambos verificados en CI).
(−) Consultas analíticas sobre campos internos requieren columnas dedicadas (se agregan según necesidad, p. ej. `fecha_refuerzo`, `inicio`).
