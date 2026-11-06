"""Configuración por variables de entorno (12-Factor App). Ver .env.example."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    seed_on_start: bool
    data_dir: Path
    environment: str

    @classmethod
    def from_env(cls) -> "Settings":
        url = os.getenv("DATABASE_URL", "sqlite:///./vetcare24.db")
        # la normalización del driver (postgres:// -> postgresql+psycopg2://) vive en db.normalizar_url
        return cls(
            database_url=url,
            seed_on_start=os.getenv("SEED_ON_START", "false").lower() in {"1", "true", "yes"},
            data_dir=Path(os.getenv("DATA_DIR", Path(__file__).resolve().parents[2] / "data")),
            environment=os.getenv("ENVIRONMENT", "development"),
        )
