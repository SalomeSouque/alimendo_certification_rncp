"""Moteur SQLAlchemy asynchrone et fourniture de sessions.

"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_database_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> AsyncEngine:
    """Crée le moteur et la fabrique de sessions (idempotent)."""
    global _engine, _session_factory

    if _engine is None:
        settings = get_database_settings()
        _engine = create_async_engine(
            settings.url,
            echo=settings.echo_sql,
            pool_size=settings.pool_size,
            pool_pre_ping=True,  # recycle une connexion coupée par le serveur
        )
        _session_factory = async_sessionmaker(
            _engine,
            expire_on_commit=False,  # les objets restent lisibles après commit
            autoflush=False,
        )
    return _engine


async def dispose_engine() -> None:
    """Ferme pool de connexions """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI : fournit une session par requête HTTP.
    """
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None  # garanti par init_engine()

    async with _session_factory() as session:
        yield session
