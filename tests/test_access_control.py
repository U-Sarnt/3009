"""Tests for access controller behavior."""

from __future__ import annotations

import gc
import os
import sys
import tempfile
import time
import uuid as uuid_lib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import close_all_sessions

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.access_control import AccessController
from core.config import Config
from core.database import (
    AccessLog,
    User,
    get_session,
    init_database,
    reset_database_engine,
)
from core.qr_handler import QRHandler


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


class TestAccessControl:
    def setup_method(self):
        self.original_db_path = Config.DB_PATH
        self.temp_dir = tempfile.TemporaryDirectory(prefix="qr_access_control_")
        self.temp_db = Path(self.temp_dir.name) / "test.db"
        Config.DB_PATH = self.temp_db
        reset_database_engine()
        init_database()

        self.controller = AccessController()

        session = get_session()
        self.test_uuid = str(uuid_lib.uuid4())
        session.add(
            User(
                uuid=self.test_uuid,
                name="Test User",
                email="test@example.com",
            )
        )
        session.commit()
        session.close()

    def teardown_method(self):
        self.controller = None
        _cleanup_sqlite_artifacts(self.temp_db)
        self.temp_dir.cleanup()
        Config.DB_PATH = self.original_db_path

    def _create_valid_qr(self, user_uuid: str) -> str:
        payload = QRHandler.build_payload(
            user_uuid=user_uuid,
            name="Test User",
            email="test@example.com",
        )
        return QRHandler.encode_payload(payload)

    def test_process_valid_qr(self):
        result = self.controller.process_qr_code(self._create_valid_qr(self.test_uuid))

        assert result["success"] is True
        assert result["access_type"] == "entry"
        assert result["user"] == "Test User"

    def test_process_invalid_qr(self):
        result = self.controller.process_qr_code("invalid qr data")

        assert result["success"] is False
        assert "invalido" in result["message"].lower()

    def test_process_unregistered_user(self):
        result = self.controller.process_qr_code(
            self._create_valid_qr(str(uuid_lib.uuid4()))
        )

        assert result["success"] is False
        assert "no registrado" in result["message"].lower()

    def test_process_inactive_user(self):
        session = get_session()
        user = session.query(User).filter_by(uuid=self.test_uuid).first()
        user.is_active = False
        session.commit()
        session.close()
        AccessController.invalidate_user_cache(self.test_uuid)

        result = self.controller.process_qr_code(self._create_valid_qr(self.test_uuid))

        assert result["success"] is False
        assert "inactivo" in result["message"].lower()

    def test_cooldown_period(self):
        qr_data = self._create_valid_qr(self.test_uuid)
        first = self.controller.process_qr_code(qr_data)
        second = self.controller.process_qr_code(qr_data)

        assert first["success"] is True
        assert second["success"] is False
        assert second["code"] == "cooldown"

    def test_entry_exit_alternation(self):
        qr_data = self._create_valid_qr(self.test_uuid)
        first = self.controller.process_qr_code(qr_data)
        self.controller.last_access[self.test_uuid] = datetime.now(UTC).replace(
            tzinfo=None
        ) - timedelta(seconds=Config.ACCESS_COOLDOWN_SECONDS + 1)
        second = self.controller.process_qr_code(qr_data)

        assert first["access_type"] == "entry"
        assert second["access_type"] == "exit"

    def test_get_recent_logs(self):
        session = get_session()
        for index in range(5):
            session.add(
                AccessLog(
                    user_uuid=self.test_uuid,
                    access_type="entry" if index % 2 == 0 else "exit",
                )
            )
        session.commit()
        session.close()

        logs = self.controller.get_recent_logs(3)

        assert len(logs) <= 3
        for log in logs:
            assert {"user", "timestamp", "access_type"} <= set(log)
