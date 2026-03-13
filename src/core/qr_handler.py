"""QR generation and signature validation helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .config import Config
from .platform_utils import sanitize_filename


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return _b64_encode(digest)


def _verify_signature(payload_bytes: bytes, signature_b64: str, secret: str) -> bool:
    try:
        expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
        received = _b64_decode(signature_b64)
        return hmac.compare_digest(expected, received)
    except Exception:
        return False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso8601(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


class QRHandler:
    """Generate and validate signed QR payloads."""

    REQUIRED_FIELDS = ("uuid", "name", "email")

    @staticmethod
    def build_payload(user_uuid: str, name: str, email: str, **extra: Any) -> Dict[str, Any]:
        payload = {
            "uuid": user_uuid,
            "name": name,
            "email": email,
        }
        payload.update(extra)
        return payload

    @staticmethod
    def encode_payload(payload: Dict[str, Any]) -> str:
        normalized = dict(payload)
        normalized.setdefault("version", Config.QR_SIGNATURE_VERSION)
        normalized.setdefault("issued_at", _to_iso8601(_utc_now()))

        if normalized.get("expires_at") is None and Config.QR_EXPIRY_HOURS:
            expires_at = _utc_now() + timedelta(hours=Config.QR_EXPIRY_HOURS)
            normalized["expires_at"] = _to_iso8601(expires_at)

        payload_json = json.dumps(
            normalized,
            separators=(",", ":"),
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")

        payload_b64 = _b64_encode(payload_json)
        signature = _sign_payload(payload_json, Config.SECRET_KEY)
        return f"{payload_b64}.{signature}"

    @staticmethod
    def _validate_payload_dict(payload: Dict[str, Any]) -> Tuple[bool, str]:
        for field_name in QRHandler.REQUIRED_FIELDS:
            value = payload.get(field_name)
            if not isinstance(value, str) or not value.strip():
                return False, f"Missing or invalid field: {field_name}"

        expires_at = payload.get("expires_at")
        if expires_at:
            try:
                expiry = _parse_timestamp(str(expires_at))
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry < _utc_now():
                    return False, "QR expired"
            except ValueError:
                return False, "Invalid expires_at timestamp"

        return True, ""

    @staticmethod
    def decode_payload(qr_text: str) -> Tuple[bool, Dict[str, Any]]:
        try:
            if "." not in qr_text:
                return False, {"error": "Invalid QR format"}

            payload_b64, signature = qr_text.split(".", 1)
            payload_bytes = _b64_decode(payload_b64)

            if not _verify_signature(payload_bytes, signature, Config.SECRET_KEY):
                return False, {"error": "Invalid signature"}

            payload = json.loads(payload_bytes.decode("utf-8"))
            is_valid, error_message = QRHandler._validate_payload_dict(payload)
            if not is_valid:
                return False, {"error": error_message}

            return True, payload
        except Exception as exc:
            return False, {"error": str(exc)}

    @staticmethod
    def validate_qr_data(qr_text: str) -> Tuple[bool, Dict[str, Any]]:
        """Backward-compatible wrapper kept for legacy tests and tools."""
        return QRHandler.decode_payload(qr_text)

    @staticmethod
    def generate_qr_file(
        payload: Dict[str, Any],
        out_dir: Optional[Path] = None,
        filename_prefix: str = "qr",
    ) -> Tuple[Path, str]:
        if out_dir is None:
            out_dir = Config.QR_OUTPUT_DIR

        out_dir.mkdir(parents=True, exist_ok=True)
        qr_text = QRHandler.encode_payload(payload)

        try:
            import qrcode
        except ImportError as exc:
            raise RuntimeError(
                "qrcode is not installed. Install project dependencies first."
            ) from exc

        qr_image = qrcode.make(qr_text)

        import time

        timestamp = int(time.time())
        safe_prefix = sanitize_filename(filename_prefix)
        file_path = out_dir / f"{safe_prefix}_{timestamp}.png"
        qr_image.save(file_path)
        return file_path, qr_text

    @staticmethod
    def generate_qr_code(user_uuid: str, name: str, email: str, **extra: Any) -> Path:
        """Backward-compatible convenience helper used by legacy scripts."""
        payload = QRHandler.build_payload(user_uuid, name, email, **extra)
        file_path, _ = QRHandler.generate_qr_file(payload, filename_prefix=f"qr_{name}")
        return file_path
