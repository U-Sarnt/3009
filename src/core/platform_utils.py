"""Platform helpers used across the project."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Union


def sanitize_filename(value: str, replacement: str = "_") -> str:
    """Convert arbitrary text into a safe filename fragment."""
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", replacement, value.strip())
    sanitized = re.sub(rf"{re.escape(replacement)}+", replacement, sanitized)
    sanitized = sanitized.strip(replacement)
    return sanitized or "item"


def open_in_file_manager(target: Union[str, Path]) -> bool:
    """Open a path or its parent folder using the platform file manager."""
    path = Path(target)
    folder = path.parent if path.is_file() else path

    try:
        if os.name == "nt":
            os.startfile(str(folder))
            return True

        command = ["open", str(folder)] if sys.platform == "darwin" else ["xdg-open", str(folder)]
        subprocess.run(command, check=False)
        return True
    except Exception:
        return False
