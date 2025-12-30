"""Output helpers for files and stdout."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional


def write_output(content: str, *, output_path: Optional[str], stdout: bool) -> None:
    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
    if stdout or not output_path:
        sys.stdout.write(content)
