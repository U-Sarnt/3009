#!/usr/bin/env python3
"""Desktop entry point for the QR access control app."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication

from core import Config, init_database
from ui.main_window import MainWindow


def configure_logging() -> None:
    """Configure file and console logging for local runs."""
    Config.ensure_dirs()
    log_file = Config.LOGS_DIR / "app.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def main() -> int:
    configure_logging()
    Config.save_default_config()
    init_database()

    app = QApplication(sys.argv)
    app.setApplicationName(Config.PROJECT_NAME)
    app.setOrganizationName(Config.ORGANIZATION_NAME)
    if hasattr(app, "setApplicationDisplayName"):
        app.setApplicationDisplayName(Config.PROJECT_NAME)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
