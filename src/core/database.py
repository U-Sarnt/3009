"""Database models and session management."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    create_engine,
    event,
)
from sqlalchemy.orm import (
    close_all_sessions,
    declarative_base,
    scoped_session,
    sessionmaker,
)

from .config import Config

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None
_engine_url = None

Base = declarative_base()


def utcnow_naive() -> datetime:
    """Return a UTC datetime without tzinfo for SQLite compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


def _current_db_url() -> str:
    return f"sqlite:///{Path(Config.DB_PATH).resolve()}"


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Enable foreign key checks for every SQLite connection."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def _migrate_access_logs_schema(db_path: Path) -> None:
    """Upgrade legacy access_logs tables and remove orphaned log rows."""
    if not db_path.exists():
        return

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if "users" not in tables or "access_logs" not in tables:
            return

        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(access_logs)"
        ).fetchall()
        has_user_fk = any(
            row[2] == "users" and row[3] == "user_uuid" and row[4] == "uuid"
            for row in foreign_keys
        )
        orphan_count = connection.execute("""
            SELECT COUNT(*)
            FROM access_logs
            WHERE user_uuid NOT IN (SELECT uuid FROM users)
            """).fetchone()[0]

        if has_user_fk and orphan_count == 0:
            return

        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("DROP TABLE IF EXISTS access_logs_new")
        connection.execute("""
            CREATE TABLE access_logs_new (
                id INTEGER NOT NULL PRIMARY KEY,
                user_uuid VARCHAR(36) NOT NULL,
                access_type VARCHAR(10) NOT NULL,
                timestamp DATETIME NOT NULL,
                CONSTRAINT ck_access_logs_access_type
                    CHECK (access_type IN ('entry', 'exit')),
                FOREIGN KEY(user_uuid) REFERENCES users (uuid)
            )
            """)
        connection.execute("""
            INSERT INTO access_logs_new (id, user_uuid, access_type, timestamp)
            SELECT access_logs.id, access_logs.user_uuid, access_logs.access_type,
                   access_logs.timestamp
            FROM access_logs
            JOIN users ON users.uuid = access_logs.user_uuid
            """)
        connection.execute("DROP TABLE access_logs")
        connection.execute("ALTER TABLE access_logs_new RENAME TO access_logs")
        connection.execute(
            "CREATE INDEX ix_access_logs_user_uuid ON access_logs (user_uuid)"
        )
        connection.execute(
            "CREATE INDEX ix_access_logs_timestamp ON access_logs (timestamp)"
        )
        connection.commit()
        connection.execute("PRAGMA foreign_keys=ON")

        if orphan_count:
            logger.warning(
                "Removed %s orphaned access log(s) while migrating %s",
                orphan_count,
                db_path,
            )


def reset_database_engine() -> None:
    """Dispose the current engine so tests and tools can swap databases safely."""
    global _engine, _session_factory, _engine_url

    close_all_sessions()

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
        _migrate_access_logs_schema(Path(Config.DB_PATH).resolve())
        _engine = create_engine(
            db_url,
            echo=Config.DB_ECHO,
            connect_args={"check_same_thread": False},
            future=True,
        )
        event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
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
    user_uuid = Column(
        String(36),
        ForeignKey("users.uuid"),
        nullable=False,
        index=True,
    )
    access_type = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=utcnow_naive, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<AccessLog {self.user_uuid} at {self.timestamp}>"
