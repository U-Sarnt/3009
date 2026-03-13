"""Tests for database models and engine lifecycle."""

from __future__ import annotations

import gc
import os
import sqlite3
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import close_all_sessions

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import Config
from core.database import (
    AccessLog,
    User,
    get_engine,
    get_session,
    init_database,
    reset_database_engine,
)


def _cleanup_sqlite_artifacts(db_path: Path) -> None:
    close_all_sessions()
    reset_database_engine()
    gc.collect()

    for suffix in ("", "-journal", "-wal", "-shm"):
        candidate = Path(f"{db_path}{suffix}")
        for attempt in range(5):
            try:
                candidate.unlink(missing_ok=True)
                break
            except PermissionError:
                if os.name != "nt" or attempt == 4:
                    raise
                time.sleep(0.1)
                gc.collect()


class TestDatabase:
    def setup_method(self):
        self.original_db_path = Config.DB_PATH
        self.temp_dir = tempfile.TemporaryDirectory(prefix="qr_access_db_")
        self.temp_db = Path(self.temp_dir.name) / "test.db"
        Config.DB_PATH = self.temp_db
        reset_database_engine()
        init_database()

    def teardown_method(self):
        _cleanup_sqlite_artifacts(self.temp_db)
        self.temp_dir.cleanup()
        Config.DB_PATH = self.original_db_path

    def test_create_user(self):
        session = get_session()
        session.add(
            User(
                uuid=str(uuid.uuid4()),
                name="Usuario 1",
                email="usuario1@example.com",
            )
        )
        session.commit()

        saved_user = session.query(User).filter_by(email="usuario1@example.com").first()
        assert saved_user is not None
        assert saved_user.name == "Usuario 1"
        assert saved_user.is_active is True
        session.close()

    def test_unique_email_constraint(self):
        session = get_session()
        session.add(
            User(
                uuid=str(uuid.uuid4()),
                name="Usuario 1",
                email="duplicado@example.com",
            )
        )
        session.commit()

        session.add(
            User(
                uuid=str(uuid.uuid4()),
                name="Usuario 2",
                email="duplicado@example.com",
            )
        )
        with pytest.raises(Exception):
            session.commit()
        session.close()

    def test_unique_uuid_constraint(self):
        session = get_session()
        shared_uuid = str(uuid.uuid4())

        session.add(
            User(uuid=shared_uuid, name="Usuario 1", email="usuario1@example.com")
        )
        session.commit()
        session.add(
            User(uuid=shared_uuid, name="Usuario 2", email="usuario2@example.com")
        )

        with pytest.raises(Exception):
            session.commit()
        session.close()

    def test_create_access_log(self):
        session = get_session()
        user_uuid = str(uuid.uuid4())
        session.add(
            User(uuid=user_uuid, name="Operador 1", email="operador1@example.com")
        )
        session.commit()

        session.add(AccessLog(user_uuid=user_uuid, access_type="entry"))
        session.commit()

        saved_log = session.query(AccessLog).filter_by(user_uuid=user_uuid).first()
        assert saved_log is not None
        assert saved_log.access_type == "entry"
        assert isinstance(saved_log.timestamp, datetime)
        session.close()

    def test_repr_methods(self):
        user = User(
            uuid=str(uuid.uuid4()),
            name="Visitante 1",
            email="visitante1@example.com",
        )
        log = AccessLog(
            user_uuid=user.uuid,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            access_type="entry",
        )

        assert repr(user) == "<User Visitante 1>"
        assert repr(log) == f"<AccessLog {user.uuid} at 2024-01-01 12:00:00>"

    def test_engine_reloads_when_db_path_changes(self):
        first_engine = get_engine()

        second_temp_dir = tempfile.TemporaryDirectory(prefix="qr_access_db_reload_")
        second_temp_db = Path(second_temp_dir.name) / "test.db"
        try:
            Config.DB_PATH = second_temp_db
            second_engine = get_engine()
            assert first_engine is not second_engine
        finally:
            first_engine = None
            second_engine = None
            _cleanup_sqlite_artifacts(second_temp_db)
            second_temp_dir.cleanup()

    def test_access_log_requires_existing_user(self):
        session = get_session()
        session.add(AccessLog(user_uuid=str(uuid.uuid4()), access_type="entry"))

        with pytest.raises(IntegrityError):
            session.commit()

        session.close()

    def test_init_database_migrates_legacy_access_logs_and_removes_orphans(self):
        reset_database_engine()

        with sqlite3.connect(self.temp_db) as connection:
            connection.execute("DROP TABLE IF EXISTS access_logs")
            connection.execute("DROP TABLE IF EXISTS users")
            connection.execute("""
                CREATE TABLE users (
                    id INTEGER NOT NULL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """)
            connection.execute("""
                CREATE TABLE access_logs (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_uuid VARCHAR(36) NOT NULL,
                    access_type VARCHAR(10) NOT NULL,
                    timestamp DATETIME NOT NULL,
                    CONSTRAINT ck_access_logs_access_type
                        CHECK (access_type IN ('entry', 'exit'))
                )
                """)

            valid_uuid = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO users (uuid, name, email, is_active, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    valid_uuid,
                    "Usuario legado",
                    "usuario.legado@example.com",
                    1,
                    "2024-01-01 00:00:00",
                ),
            )
            connection.execute(
                """
                INSERT INTO access_logs (user_uuid, access_type, timestamp)
                VALUES (?, ?, ?)
                """,
                (valid_uuid, "entry", "2024-01-01 01:00:00"),
            )
            connection.execute(
                """
                INSERT INTO access_logs (user_uuid, access_type, timestamp)
                VALUES (?, ?, ?)
                """,
                (str(uuid.uuid4()), "exit", "2024-01-01 02:00:00"),
            )
            connection.commit()

        init_database()

        with sqlite3.connect(self.temp_db) as connection:
            fk_rows = connection.execute(
                "PRAGMA foreign_key_list(access_logs)"
            ).fetchall()
            access_logs = connection.execute(
                "SELECT user_uuid, access_type FROM access_logs ORDER BY id"
            ).fetchall()

        assert any(
            row[2] == "users" and row[3] == "user_uuid" and row[4] == "uuid"
            for row in fk_rows
        )
        assert access_logs == [(valid_uuid, "entry")]
