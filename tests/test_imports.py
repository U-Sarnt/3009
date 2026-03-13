"""Smoke tests for importability of top-level modules."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_ui_and_tools_modules():
    from ui.main_window import MainWindow  # noqa: F401
    from ui.admin_dialog import AdminDialog  # noqa: F401
    from tools.backup_db import create_backup  # noqa: F401
    from tools.export_logs import export_logs  # noqa: F401
    from tools.generate_qr import main as generate_qr_main  # noqa: F401

    assert MainWindow is not None
    assert AdminDialog is not None
    assert create_backup is not None
    assert export_logs is not None
    assert generate_qr_main is not None
