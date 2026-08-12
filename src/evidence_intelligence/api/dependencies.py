"""FastAPI dependency providers. Overridden in tests with fakes so
contract/integration tests don't require a live Postgres/GEE connection."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from evidence_intelligence.config import Settings
from evidence_intelligence.config import settings as default_settings
from evidence_intelligence.store.evidence_store import EvidenceStore

_engine = None
_SessionLocal = None


def _get_session_factory(database_url: str):
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine(database_url)
        _SessionLocal = sessionmaker(bind=_engine)
    return _SessionLocal


def get_settings() -> Settings:
    return default_settings


def get_session() -> Generator[Session, None, None]:
    session_factory = _get_session_factory(default_settings.database_url)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_store(session: Session = Depends(get_session)) -> EvidenceStore:
    return EvidenceStore(session)
