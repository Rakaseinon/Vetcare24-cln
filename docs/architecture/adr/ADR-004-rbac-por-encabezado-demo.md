# ADR-004 — RBAC (RNF-03) con encabezado `X-Rol` para el prototipo

- **Estatus:** Aceptado (alcance PIA) · **Fecha:** 2026-11-01 · **Requisito:** RNF-03

## Contexto
RNF-03 exige que la recepción no vea información clínica (expediente, notas, recetas). El PIA pide demostrar el control de acceso en vivo,
pero no exige un sistema de identidad completo, y el tiempo del proyecto se concentra en dominio, patrones y calidad.

## Decisión
`security.requiere(*roles)` es una dependencia FastAPI que valida el encabezado `X-Rol` ∈ {RECEPCION, VETERINARIO, ENFERMERIA, DIRECTOR}
(401 si falta o es desconocido; 403 si el rol no tiene acceso). Recepción **no** accede a expediente, notas ni recetas (RNF-03).
Los roles de cada recurso se leen de esa misma dependencia para documentarlos en Swagger, de modo que documentación y código no se separan.

## Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| JWT / OAuth2 con usuarios y contraseñas | Requiere tabla de usuarios, emisión y rotación de claves y pantalla de login; desvía el esfuerzo del dominio |
| Proveedor externo (Auth0, Keycloak) | Dependencia externa y secretos que complican el Docker Compose reproducible |
| Sin control de acceso | Incumple RNF-03 y deja sin demostración una regla del BRD |

## Consecuencias y límites
Es una **demostración de autorización por rol, no autenticación**: cualquiera puede enviar el encabezado. En producción se sustituye
`requiere` por validación de JWT/OIDC sin tocar rutas ni dominio (único punto de cambio). Declarado como limitación en el reporte.
