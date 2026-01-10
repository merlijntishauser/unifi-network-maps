from __future__ import annotations

import tempfile
from pathlib import Path


def before_scenario(context, _scenario) -> None:
    context.temp_dir = tempfile.TemporaryDirectory()
    context.output_dir = Path(context.temp_dir.name)


def after_scenario(context, _scenario) -> None:
    temp_dir = getattr(context, "temp_dir", None)
    if temp_dir:
        temp_dir.cleanup()
