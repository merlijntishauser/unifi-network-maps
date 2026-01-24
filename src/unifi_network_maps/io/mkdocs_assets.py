"""MkDocs asset output helpers."""

from __future__ import annotations

from pathlib import Path

from ..render.templating import render_template
from .paths import resolve_output_file


def write_mkdocs_sidebar_assets(output_path: str | Path) -> None:
    resolved = resolve_output_file(output_path, extensions=None, label="MkDocs output file")
    output_dir = resolved.parent
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "legend.js").write_text(
        render_template("mkdocs_legend.js.j2"),
        encoding="utf-8",
    )
    (assets_dir / "legend.css").write_text(
        render_template("mkdocs_legend.css.j2"),
        encoding="utf-8",
    )
