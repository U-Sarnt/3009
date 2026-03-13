"""Database models and session management."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from .config import Config

_engine = None
_session_factory = None
_engine_url = None

Base = declarative_base()


def utcnow_naive() -> datetime:
    """Return a UTC datetime without tzinfo for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


def _current_db_url() -> str:
    return f"sqlite:///{Path(Config.DB_PATH).resolve()}"


def reset_database_engine() -> None:
    """Dispose the current engine so tests and tools can swap databases safely."""
    global _engine, _session_factory, _engine_url

    if _session_factory is not None:
        _session_factory.remove()
        _session_factory = None

    if _engine is not None:
        _engine.dispose()
        _engine = None

    _engine_url = None


def get_engine():
    """Return a lazily-initialized engine bound to the current Config.DB_PATH."""
    global _engine, _session_factory, _engine_url

    db_url = _current_db_url()
    if _engine is None or _engine_url != db_url:
        reset_database_engine()
        _engine = create_engine(
            db_url,
            echo=Config.DB_ECHO,
            connect_args={"check_same_thread": False},
            future=True,
        )
        _session_factory = scoped_session(
            sessionmaker(bind=_engine, autoflush=False, autocommit=False)
        )
        _engine_url = db_url

    return _engine


def init_database() -> None:
    """Create tables if they do not exist."""
    Config.ensure_dirs()
    Base.metadata.create_all(get_engine())


def get_session():
    """Return a scoped SQLAlchemy session."""
    get_engine()
    return _session_factory()


class User(Base):
    """Registered user allowed to scan access QR codes."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)

    def __repr__(self) -> str:
        return f"<User {self.name}>"


class AccessLog(Base):
    """Access records generated after successful scans."""

    __tablename__ = "access_logs"
    __table_args__ = (
        CheckConstraint(
            "access_type IN ('entry', 'exit')",
            name="ck_access_logs_access_type",
        ),
    )

    id = Column(Integer, primary_key=True)
    user_uuid = Column(String(36), nullable=False, index=True)
    access_type = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=utcnow_naive, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<AccessLog {self.user_uuid} at {self.timestamp}>"
