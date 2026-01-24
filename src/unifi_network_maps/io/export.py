"""Output helpers for files and stdout."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from .paths import resolve_output_path


def write_output(
    content: str,
    *,
    output_path: str | Path | None,
    stdout: bool,
    format_name: str | None = None,
) -> None:
    if output_path:
        resolved = resolve_output_path(output_path, format_name=format_name)
        _write_atomic(resolved, content)
    if stdout or not output_path:
        sys.stdout.write(content)


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        tmp_path = Path(temp_file.name)
    tmp_path.replace(path)
