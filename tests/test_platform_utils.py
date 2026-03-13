"""Tests for platform-specific utility helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core import platform_utils


def test_open_in_file_manager_returns_false_for_missing_target(tmp_path):
    missing = tmp_path / "missing-folder"
    assert platform_utils.open_in_file_manager(missing) is False


def test_open_in_file_manager_checks_subprocess_result(tmp_path, monkeypatch):
    folder = tmp_path / "exports"
    folder.mkdir()

    calls = []

    class CompletedProcess:
        def __init__(self, returncode: int):
            self.returncode = returncode

    def fake_run(command, check):
        calls.append((command, check))
        return CompletedProcess(returncode=0)

    monkeypatch.setattr(platform_utils.subprocess, "run", fake_run)
    monkeypatch.setattr(platform_utils.os, "name", "posix")
    monkeypatch.setattr(platform_utils.sys, "platform", "linux")

    assert platform_utils.open_in_file_manager(folder) is True
    assert calls == [(["xdg-open", str(folder)], False)]


def test_open_in_file_manager_returns_false_on_failed_subprocess(tmp_path, monkeypatch):
    folder = tmp_path / "reports"
    folder.mkdir()

    class CompletedProcess:
        def __init__(self, returncode: int):
            self.returncode = returncode

    monkeypatch.setattr(
        platform_utils.subprocess,
        "run",
        lambda command, check: CompletedProcess(returncode=1),
    )
    monkeypatch.setattr(platform_utils.os, "name", "posix")
    monkeypatch.setattr(platform_utils.sys, "platform", "linux")

    assert platform_utils.open_in_file_manager(folder) is False
