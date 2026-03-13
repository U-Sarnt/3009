"""Tests for CLI helper modules."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import Config
from core.database import (
    AccessLog,
    User,
    get_session,
    init_database,
    reset_database_engine,
)
from tools.backup_db import create_backup, verify_backup_integrity
from tools.export_logs import export_logs


class TestTools:
    def setup_method(self):
        self.temp_root = Path(tempfile.mkdtemp(prefix="qr_access_tools_"))
        self.original_paths = {
            "DATA_DIR": Config.DATA_DIR,
            "QR_OUTPUT_DIR": Config.QR_OUTPUT_DIR,
            "DB_PATH": Config.DB_PATH,
            "LOGS_DIR": Config.LOGS_DIR,
            "BACKUPS_DIR": Config.BACKUPS_DIR,
            "SECRET_FILE": Config.SECRET_FILE,
        }
        self.original_env = {
            "QR_DATA_DIR": os.environ.get("QR_DATA_DIR"),
            "QR_SECRET_FILE": os.environ.get("QR_SECRET_FILE"),
        }

        os.environ["QR_DATA_DIR"] = str(self.temp_root / "data")
        os.environ["QR_SECRET_FILE"] = str(self.temp_root / ".secret_key")

        Config.refresh_runtime_paths()
        Config.DATA_DIR = Path(os.environ["QR_DATA_DIR"])
        Config.QR_OUTPUT_DIR = Config.DATA_DIR / "qr_codes"
        Config.DB_PATH = Config.DATA_DIR / "database.db"
        Config.LOGS_DIR = self.temp_root / "logs"
        Config.BACKUPS_DIR = self.temp_root / "backups"
        Config.ensure_dirs()

        reset_database_engine()
        init_database()

        session = get_session()
        try:
            user = User(
                uuid=str(uuid.uuid4()), name="Tools User", email="tools@example.com"
            )
            session.add(user)
            session.flush()
            session.add(AccessLog(user_uuid=user.uuid, access_type="entry"))
            session.commit()
        finally:
            session.close()

        (Config.QR_OUTPUT_DIR / "sample.png").write_bytes(b"fake png")
        (Config.LOGS_DIR / "app.log").write_text("log line\n", encoding="utf-8")

    def teardown_method(self):
        reset_database_engine()
        for name, value in self.original_paths.items():
            setattr(Config, name, value)
        for name, value in self.original_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        Config.refresh_runtime_paths()
        Config.ensure_dirs()

        import shutil

        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_export_logs_json(self):
        output_file = self.temp_root / "access_logs.json"
        result = export_logs(days_back=30, output_file=output_file, format="json")

        assert result == output_file
        payload = json.loads(output_file.read_text(encoding="utf-8"))
        assert payload["total_records"] == 1
        assert payload["records"][0]["user"]["email"] == "tools@example.com"

    def test_backup_create_and_verify(self):
        backup_file = create_backup(include_logs=True)

        assert backup_file is not None
        assert backup_file.exists()
        assert verify_backup_integrity(backup_file) is True
