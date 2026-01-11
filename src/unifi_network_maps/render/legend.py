"""Legend rendering helpers."""

from __future__ import annotations

from .mermaid import render_legend, render_legend_compact
from .mermaid_theme import MermaidTheme


def resolve_legend_style(*, format_name: str, legend_style: str) -> str:
    if legend_style == "auto":
        return "compact" if format_name == "mkdocs" else "diagram"
    return legend_style


def render_legend_only(
    *,
    legend_style: str,
    legend_scale: float,
    markdown: bool,
    theme: MermaidTheme,
) -> str:
    if legend_style == "compact":
        content = "# Legend\n\n" + render_legend_compact(theme=theme)
    else:
        content = render_legend(theme=theme, legend_scale=legend_scale)
    if markdown:
        content = f"""```mermaid
{content}```
"""
    return content
