"""Tests for database models and engine lifecycle."""

from __future__ import annotations

import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import Config
from core.database import AccessLog, User, get_engine, get_session, init_database, reset_database_engine


class TestDatabase:
    def setup_method(self):
        self.original_db_path = Config.DB_PATH
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        Config.DB_PATH = Path(self.temp_db.name)
        reset_database_engine()
        init_database()

    def teardown_method(self):
        reset_database_engine()
        Config.DB_PATH = self.original_db_path
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_create_user(self):
        session = get_session()
        session.add(User(uuid=str(uuid.uuid4()), name="Test User", email="test@example.com"))
        session.commit()

        saved_user = session.query(User).filter_by(email="test@example.com").first()
        assert saved_user is not None
        assert saved_user.name == "Test User"
        assert saved_user.is_active is True
        session.close()

    def test_unique_email_constraint(self):
        session = get_session()
        session.add(User(uuid=str(uuid.uuid4()), name="User 1", email="same@example.com"))
        session.commit()

        session.add(User(uuid=str(uuid.uuid4()), name="User 2", email="same@example.com"))
        with pytest.raises(Exception):
            session.commit()
        session.close()

    def test_unique_uuid_constraint(self):
        session = get_session()
        shared_uuid = str(uuid.uuid4())

        session.add(User(uuid=shared_uuid, name="User 1", email="user1@example.com"))
        session.commit()
        session.add(User(uuid=shared_uuid, name="User 2", email="user2@example.com"))

        with pytest.raises(Exception):
            session.commit()
        session.close()

    def test_create_access_log(self):
        session = get_session()
        user_uuid = str(uuid.uuid4())
        session.add(User(uuid=user_uuid, name="Test User", email="test@example.com"))
        session.commit()

        session.add(AccessLog(user_uuid=user_uuid, access_type="entry"))
        session.commit()

        saved_log = session.query(AccessLog).filter_by(user_uuid=user_uuid).first()
        assert saved_log is not None
        assert saved_log.access_type == "entry"
        assert isinstance(saved_log.timestamp, datetime)
        session.close()

    def test_repr_methods(self):
        user = User(uuid=str(uuid.uuid4()), name="John Doe", email="john@example.com")
        log = AccessLog(user_uuid=user.uuid, timestamp=datetime(2024, 1, 1, 12, 0, 0), access_type="entry")

        assert repr(user) == "<User John Doe>"
        assert repr(log) == f"<AccessLog {user.uuid} at 2024-01-01 12:00:00>"

    def test_engine_reloads_when_db_path_changes(self):
        first_engine = get_engine()

        second_temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        try:
            Config.DB_PATH = Path(second_temp_db.name)
            second_engine = get_engine()
            assert first_engine is not second_engine
        finally:
            reset_database_engine()
            Path(second_temp_db.name).unlink(missing_ok=True)
