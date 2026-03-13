"""Tests for QR payload generation and validation."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import Config
from core.qr_handler import QRHandler


class TestQRHandler:
    def setup_method(self):
        Config.ensure_dirs()

    def test_validate_qr_valid(self):
        qr_text = QRHandler.encode_payload(
            QRHandler.build_payload("test-uuid", "Test User", "test@example.com")
        )

        is_valid, payload = QRHandler.validate_qr_data(qr_text)

        assert is_valid is True
        assert payload["uuid"] == "test-uuid"
        assert payload["name"] == "Test User"
        assert "issued_at" in payload
        assert "expires_at" in payload

    def test_validate_qr_invalid_signature(self):
        qr_text = QRHandler.encode_payload(
            QRHandler.build_payload("test-uuid", "Test User", "test@example.com")
        )
        payload_b64, signature = qr_text.split(".", 1)
        tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
        tampered = f"{payload_b64}.{tampered_signature}"

        is_valid, data = QRHandler.validate_qr_data(tampered)

        assert is_valid is False
        assert data["error"] == "Invalid signature"

    def test_validate_qr_invalid_structure(self):
        is_valid, data = QRHandler.validate_qr_data("not-a-signed-qr")
        assert is_valid is False
        assert "format" in data["error"].lower()

    def test_validate_qr_expired(self):
        expired_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        qr_text = QRHandler.encode_payload(
            QRHandler.build_payload(
                "test-uuid",
                "Test User",
                "test@example.com",
                expires_at=expired_at,
            )
        )

        is_valid, data = QRHandler.validate_qr_data(qr_text)

        assert is_valid is False
        assert data["error"] == "QR expired"

    def test_generate_qr_code_legacy_wrapper(self):
        pytest.importorskip("qrcode")

        qr_path = QRHandler.generate_qr_code(
            "test-uuid-123", "Test User", "test@example.com"
        )

        assert qr_path.exists()
        assert qr_path.suffix == ".png"
        qr_path.unlink()
