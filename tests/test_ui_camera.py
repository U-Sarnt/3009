"""Integration-oriented tests for Qt UI and camera helpers."""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtWidgets import QApplication

from core.camera import CameraThread, open_video_capture
from core.config import Config
from core.database import User, get_session, init_database, reset_database_engine
from core.qr_handler import QRHandler
from ui.main_window import MainWindow


def ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestMainWindow:
    def setup_method(self):
        self.original_db_path = Config.DB_PATH
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        Config.DB_PATH = Path(self.temp_db.name)
        reset_database_engine()
        init_database()

        session = get_session()
        self.user_uuid = str(uuid.uuid4())
        session.add(
            User(
                uuid=self.user_uuid,
                name="Qt User",
                email="qt@example.com",
            )
        )
        session.commit()
        session.close()

    def teardown_method(self):
        reset_database_engine()
        Config.DB_PATH = self.original_db_path
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_process_qr_updates_status_and_recent_access(self):
        ensure_app()
        window = MainWindow()
        window.update_timer.stop()

        qr_text = QRHandler.encode_payload(
            QRHandler.build_payload(self.user_uuid, "Qt User", "qt@example.com")
        )
        window.process_qr(qr_text)

        assert window.status_label.text() == "ENTRY: Qt User"
        assert window.status_label.property("status") == "success"
        assert "Qt User - ENTRY" in window.last_access_label.text()

        window.close()


def test_open_video_capture_retries_backends(monkeypatch):
    captures = []

    class DummyCapture:
        def __init__(self, opened: bool):
            self.opened = opened
            self.released = False

        def isOpened(self):
            return self.opened

        def release(self):
            self.released = True

    def fake_video_capture(index, backend=None):
        capture = DummyCapture(opened=backend == "good-backend")
        captures.append((index, backend, capture))
        return capture

    monkeypatch.setattr(
        "core.camera._backend_candidates", lambda: ["bad", "good-backend"]
    )
    monkeypatch.setattr("core.camera.cv2.VideoCapture", fake_video_capture)

    capture = open_video_capture(7)

    assert capture is captures[1][2]
    assert captures[0][2].released is True
    assert captures[1][0:2] == (7, "good-backend")


def test_camera_thread_detect_qr_codes_respects_cooldown():
    ensure_app()
    thread = CameraThread()
    emissions = []

    class FakeDetector:
        def detectAndDecode(self, frame):
            return ("signed-qr-data", None, None)

    thread.qr_detector = FakeDetector()
    thread.qr_detected.connect(emissions.append)

    thread.detect_qr_codes(object())
    thread.detect_qr_codes(object())

    assert emissions == ["signed-qr-data"]

    thread.qr_cooldown = 0
    thread.detect_qr_codes(object())

    assert emissions == ["signed-qr-data", "signed-qr-data"]
