"""Exporta el contrato OpenAPI a docs/api/openapi.json.  Uso: python scripts/exportar_openapi.py [salida]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.api.main import create_app  # noqa: E402
from src.infrastructure.config import Settings  # noqa: E402

if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "api" / "openapi.json"
    app = create_app(Settings("sqlite://", False, ROOT / "data", "docs"))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OpenAPI escrito en {destino} ({len(app.openapi()['paths'])} rutas)")
