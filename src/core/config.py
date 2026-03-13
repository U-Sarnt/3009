"""Application configuration for the QR access control project."""

from __future__ import annotations

import json
import os
import secrets
import warnings
from pathlib import Path


class Config:
    """Centralized runtime configuration."""

    ORGANIZATION_NAME = "U-Sarnt"
    PRODUCT_NAME = "QR Access Control"
    PROJECT_NAME = f"{ORGANIZATION_NAME} {PRODUCT_NAME}"
    COPYRIGHT_NOTICE = "Copyright (c) U-Sarnt. All rights reserved."

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    SRC_DIR = Path(__file__).resolve().parents[1]

    DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
    LEGACY_DATA_DIR = SRC_DIR / "data"
    DEFAULT_SECRET_FILE = PROJECT_ROOT / ".secret_key"
    LEGACY_SECRET_FILE = SRC_DIR / ".secret_key"

    DATA_DIR = DEFAULT_DATA_DIR
    QR_OUTPUT_DIR = DATA_DIR / "qr_codes"
    DB_PATH = DATA_DIR / "database.db"
    CONFIG_FILE = PROJECT_ROOT / "config.json"
    LOGS_DIR = PROJECT_ROOT / "logs"
    BACKUPS_DIR = PROJECT_ROOT / "backups"

    DB_ECHO = False

    SECRET_FILE = DEFAULT_SECRET_FILE
    SECRET_KEY = None

    CAMERA_INDEX = 0
    CAMERA_BACKEND = None

    ACCESS_COOLDOWN_SECONDS = 3
    USER_CACHE_TTL_SECONDS = 300
    DEFAULT_RECENT_LOG_LIMIT = 10
    QR_EXPIRY_HOURS = 24 * 30
    QR_SIGNATURE_VERSION = 2

    @classmethod
    def _path_has_state(cls, candidate: Path) -> bool:
        """Return True if the directory already contains app data."""
        try:
            if not candidate.exists():
                return False
            if (candidate / "database.db").exists():
                return True
            qr_dir = candidate / "qr_codes"
            return qr_dir.exists() and any(qr_dir.iterdir())
        except OSError:
            return False

    @classmethod
    def _resolve_data_dir(cls) -> Path:
        """Resolve a data directory while keeping compatibility with legacy layouts."""
        env_data_dir = os.environ.get("QR_DATA_DIR")
        if env_data_dir:
            return Path(env_data_dir).expanduser().resolve()

        if cls._path_has_state(cls.DEFAULT_DATA_DIR):
            return cls.DEFAULT_DATA_DIR

        if cls._path_has_state(cls.LEGACY_DATA_DIR):
            return cls.LEGACY_DATA_DIR

        return cls.DEFAULT_DATA_DIR

    @classmethod
    def _resolve_secret_file(cls) -> Path:
        """Resolve the secret key file path."""
        env_secret_file = os.environ.get("QR_SECRET_FILE")
        if env_secret_file:
            return Path(env_secret_file).expanduser().resolve()

        if cls.DEFAULT_SECRET_FILE.exists():
            return cls.DEFAULT_SECRET_FILE

        if cls.LEGACY_SECRET_FILE.exists():
            return cls.LEGACY_SECRET_FILE

        return cls.DEFAULT_SECRET_FILE

    @classmethod
    def refresh_runtime_paths(cls) -> None:
        """Refresh derived paths after env/config changes."""
        current_data_dir = Path(cls.DATA_DIR)
        current_db_path = Path(cls.DB_PATH)
        managed_db_paths = {
            current_data_dir / "database.db",
            cls.DEFAULT_DATA_DIR / "database.db",
            cls.LEGACY_DATA_DIR / "database.db",
        }

        resolved_data_dir = cls._resolve_data_dir()
        cls.DATA_DIR = resolved_data_dir
        cls.QR_OUTPUT_DIR = resolved_data_dir / "qr_codes"

        if current_db_path in managed_db_paths:
            cls.DB_PATH = resolved_data_dir / "database.db"
        else:
            cls.DB_PATH = current_db_path

        cls.SECRET_FILE = cls._resolve_secret_file()

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create required runtime directories."""
        cls.refresh_runtime_paths()
        try:
            cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
            cls.QR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            cls.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
            Path(cls.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            warnings.warn(f"Could not create runtime directories: {exc}")

    @classmethod
    def _coerce_int(cls, value, fallback: int) -> int:
        """Best-effort integer coercion for config inputs."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @classmethod
    def load_config_file(cls) -> None:
        """Load optional runtime overrides from config.json."""
        if not cls.CONFIG_FILE.exists():
            return

        try:
            config = json.loads(cls.CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.warn(f"Could not load config.json: {exc}")
            return

        camera_cfg = config.get("camera", {})
        security_cfg = config.get("security", {})
        database_cfg = config.get("database", {})
        qr_cfg = config.get("qr", {})
        cache_cfg = config.get("cache", {})

        cls.CAMERA_INDEX = cls._coerce_int(camera_cfg.get("index"), cls.CAMERA_INDEX)
        cls.ACCESS_COOLDOWN_SECONDS = cls._coerce_int(
            security_cfg.get("cooldown_seconds"),
            cls.ACCESS_COOLDOWN_SECONDS,
        )
        cls.USER_CACHE_TTL_SECONDS = cls._coerce_int(
            cache_cfg.get("user_ttl_seconds"),
            cls.USER_CACHE_TTL_SECONDS,
        )
        cls.DEFAULT_RECENT_LOG_LIMIT = cls._coerce_int(
            cache_cfg.get("recent_log_limit"),
            cls.DEFAULT_RECENT_LOG_LIMIT,
        )
        cls.QR_EXPIRY_HOURS = cls._coerce_int(
            qr_cfg.get("expiry_hours"),
            cls.QR_EXPIRY_HOURS,
        )
        cls.DB_ECHO = bool(database_cfg.get("echo", cls.DB_ECHO))

    @classmethod
    def save_default_config(cls) -> None:
        """Persist a default config template for local adjustments."""
        if cls.CONFIG_FILE.exists():
            return

        default_config = {
            "camera": {
                "index": cls.CAMERA_INDEX,
            },
            "security": {
                "cooldown_seconds": cls.ACCESS_COOLDOWN_SECONDS,
            },
            "cache": {
                "user_ttl_seconds": cls.USER_CACHE_TTL_SECONDS,
                "recent_log_limit": cls.DEFAULT_RECENT_LOG_LIMIT,
            },
            "database": {
                "echo": cls.DB_ECHO,
            },
            "qr": {
                "expiry_hours": cls.QR_EXPIRY_HOURS,
            },
        }

        try:
            cls.CONFIG_FILE.write_text(
                json.dumps(default_config, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            warnings.warn(f"Could not write config.json: {exc}")

    @classmethod
    def _init_secret_key(cls) -> None:
        """Load or create the signing secret."""
        env_key = os.environ.get("QR_SECRET_KEY") or os.environ.get("SECRET_KEY")
        if env_key:
            cls.SECRET_KEY = env_key.strip()
            return

        try:
            if cls.SECRET_FILE.exists():
                saved = cls.SECRET_FILE.read_text(encoding="utf-8").strip()
                if saved:
                    cls.SECRET_KEY = saved
                    return
        except OSError:
            pass

        cls.SECRET_KEY = secrets.token_hex(32)
        try:
            cls.SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
            cls.SECRET_FILE.write_text(cls.SECRET_KEY, encoding="utf-8")
            if os.name != "nt":
                os.chmod(cls.SECRET_FILE, 0o600)
        except OSError as exc:
            warnings.warn(f"Could not write secret file: {exc}")

    @classmethod
    def bootstrap(cls) -> None:
        """Initialize runtime paths, config and secret material."""
        cls.refresh_runtime_paths()
        cls.ensure_dirs()
        cls.load_config_file()
        cls.ensure_dirs()
        cls._init_secret_key()


Config.bootstrap()
