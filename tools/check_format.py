#!/usr/bin/env python3
"""Run Black sequentially to avoid batch-mode hangs in constrained envs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def iter_python_files():
    """Yield tracked project Python files in a stable order."""
    yield ROOT / "run.py"

    for folder_name in ("src", "tests", "tools"):
        for path in sorted((ROOT / folder_name).rglob("*.py")):
            if path == Path(__file__).resolve():
                continue
            yield path


def main() -> int:
    for file_path in iter_python_files():
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "black",
                "--check",
                "--workers",
                "1",
                str(file_path),
            ],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
