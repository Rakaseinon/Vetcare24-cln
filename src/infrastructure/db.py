"""Motor y sesiones SQLAlchemy. Un único punto de conexión; la URL viene de DATABASE_URL."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def normalizar_url(url: str) -> str:
    """Render/Heroku entregan postgres://; SQLAlchemy 2 asume psycopg v3 con postgresql://, pero usamos psycopg2."""
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg2://" + url[len(prefijo):]
    return url


def make_engine(url: str) -> Engine:
    url = normalizar_url(url)
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url in {"sqlite://", "sqlite:///"}:
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=True)


def create_schema(engine: Engine) -> None:
    from . import models  # noqa: F401  (registra las tablas)
    Base.metadata.create_all(engine)
