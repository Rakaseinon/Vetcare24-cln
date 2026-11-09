"""Aplicación FastAPI de VetCare 24. Swagger UI en /docs y OpenAPI en /openapi.json.

Arranque:  uvicorn src.api.main:create_app --factory --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from ..domain.common import BusinessRuleViolation, DomainError, EntityNotFound, ValidationDomainError
from ..infrastructure.config import Settings
from .container import Container, build_container
from .docs import DESCRIPCION, TAGS, aplicar_documentacion, instalar_openapi, pagina_docs
from .routes import router


_ESTATICOS = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="VetCare 24 API", version="1.0.0", description=DESCRIPCION, openapi_tags=TAGS,
                  docs_url=None, contact={"name": "Equipo 4 · FIME-UANL"})
    app.state.container = container or build_container(settings)

    def _err(status: int):
        async def handler(_: Request, exc: DomainError) -> JSONResponse:
            return JSONResponse(status_code=status, content={"codigo": type(exc).__name__, "mensaje": str(exc)})
        return handler

    app.add_exception_handler(EntityNotFound, _err(404))
    app.add_exception_handler(ValidationDomainError, _err(400))
    app.add_exception_handler(BusinessRuleViolation, _err(409))
    app.add_exception_handler(DomainError, _err(400))

    @app.get("/health", tags=["9 · Operación"])
    def health() -> dict:
        return {"status": "ok", "environment": settings.environment}

    @app.get("/docs", include_in_schema=False)
    def swagger_ui() -> HTMLResponse:
        return pagina_docs(app.openapi_url or "/openapi.json", f"{app.title} · Swagger UI")

    @app.get("/app", include_in_schema=False)
    def interfaz_visual() -> FileResponse:
        """Interfaz web de la clínica (HTML/JS sin dependencias): consume esta misma API con el rol elegido."""
        return FileResponse(_ESTATICOS / "app.html", media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache"})

    @app.get("/", include_in_schema=False)
    def raiz() -> RedirectResponse:
        return RedirectResponse("/docs")

    app.include_router(router)
    aplicar_documentacion(app, router)
    instalar_openapi(app)
    return app
