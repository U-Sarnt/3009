"""Access control workflow for signed QR scans."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from threading import Lock
from typing import Optional

from .config import Config
from .database import AccessLog, User, get_session
from .qr_handler import QRHandler

logger = logging.getLogger(__name__)


class AccessController:
    """Main access controller used by the UI and tools."""

    _user_cache = {}
    _cache_lock = Lock()

    def __init__(self):
        self.last_access = {}

    @classmethod
    def _read_cached_user(cls, user_uuid: str):
        now = time.time()
        with cls._cache_lock:
            cached = cls._user_cache.get(user_uuid)
            if not cached:
                return None

            if now - cached["cached_at"] > Config.USER_CACHE_TTL_SECONDS:
                cls._user_cache.pop(user_uuid, None)
                return None

            return dict(cached["user"])

    @classmethod
    def _write_cached_user(cls, user: User) -> None:
        with cls._cache_lock:
            cls._user_cache[user.uuid] = {
                "cached_at": time.time(),
                "user": {
                    "uuid": user.uuid,
                    "name": user.name,
                    "email": user.email,
                    "is_active": bool(user.is_active),
                },
            }

    @classmethod
    def invalidate_user_cache(cls, user_uuid: Optional[str] = None) -> None:
        """Invalidate one cached user or the full cache."""
        with cls._cache_lock:
            if user_uuid is None:
                cls._user_cache.clear()
            else:
                cls._user_cache.pop(user_uuid, None)

    def _load_user(self, user_uuid: str):
        cached = self._read_cached_user(user_uuid)
        if cached:
            return cached

        session = get_session()
        try:
            user = session.query(User).filter_by(uuid=user_uuid).first()
            if user:
                self._write_cached_user(user)
                return {
                    "uuid": user.uuid,
                    "name": user.name,
                    "email": user.email,
                    "is_active": bool(user.is_active),
                }
            return None
        finally:
            session.close()

    def process_qr_code(self, qr_data: str) -> dict:
        """Validate a QR scan and record entry/exit access."""
        is_valid, payload = QRHandler.decode_payload(qr_data)
        if not is_valid:
            return {
                "success": False,
                "code": "invalid_qr",
                "message": f"QR invalido: {payload.get('error', 'unknown error')}",
            }

        user = self._load_user(payload["uuid"])
        if not user:
            return {
                "success": False,
                "code": "unknown_user",
                "message": "Usuario no registrado",
            }

        if not user["is_active"]:
            return {
                "success": False,
                "code": "inactive_user",
                "message": "Usuario inactivo",
            }

        now = datetime.now(UTC).replace(tzinfo=None)
        if user["uuid"] in self.last_access:
            elapsed = (now - self.last_access[user["uuid"]]).total_seconds()
            if elapsed < Config.ACCESS_COOLDOWN_SECONDS:
                remaining = max(1, int(Config.ACCESS_COOLDOWN_SECONDS - elapsed))
                return {
                    "success": False,
                    "code": "cooldown",
                    "message": f"Espere {remaining} segundos",
                }

        session = get_session()
        try:
            last_log = (
                session.query(AccessLog)
                .filter_by(user_uuid=user["uuid"])
                .order_by(AccessLog.timestamp.desc())
                .first()
            )
            access_type = "entry" if not last_log or last_log.access_type == "exit" else "exit"

            session.add(AccessLog(user_uuid=user["uuid"], access_type=access_type))
            session.commit()

            self.last_access[user["uuid"]] = now
            logger.info("Access granted for %s (%s)", user["name"], access_type)

            return {
                "success": True,
                "code": "access_granted",
                "message": f"{access_type.upper()}: {user['name']}",
                "user": user["name"],
                "access_type": access_type,
                "timestamp": now.isoformat(),
            }
        except Exception as exc:
            session.rollback()
            logger.exception("Failed to record access")
            return {
                "success": False,
                "code": "database_error",
                "message": f"Error de base de datos: {exc}",
            }
        finally:
            session.close()

    def get_recent_logs(self, limit: Optional[int] = None) -> list:
        """Return the most recent access logs with user names."""
        limit = limit or Config.DEFAULT_RECENT_LOG_LIMIT

        session = get_session()
        try:
            logs = (
                session.query(AccessLog, User)
                .join(User, User.uuid == AccessLog.user_uuid)
                .order_by(AccessLog.timestamp.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "user": user.name,
                    "timestamp": log.timestamp,
                    "access_type": log.access_type,
                }
                for log, user in logs
            ]
        finally:
            session.close()

    def get_dashboard_stats(self) -> dict:
        """Return lightweight counters for the main dashboard."""
        session = get_session()
        try:
            total_users = session.query(User).count()
            active_users = session.query(User).filter_by(is_active=True).count()
            total_logs = session.query(AccessLog).count()
            return {
                "total_users": total_users,
                "active_users": active_users,
                "total_logs": total_logs,
            }
        finally:
            session.close()
