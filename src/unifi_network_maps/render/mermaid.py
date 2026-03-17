"""Compatibility wrapper for moved Mermaid renderers."""

from __future__ import annotations

from unifi_topology.render import mermaid as _mermaid

DEFAULT_THEME = _mermaid.DEFAULT_THEME
MermaidTheme = _mermaid.MermaidTheme
class_defs = _mermaid.class_defs
render_legend = _mermaid.render_legend
render_legend_compact = _mermaid.render_legend_compact
render_mermaid = _mermaid.render_mermaid

__all__ = [
    "DEFAULT_THEME",
    "MermaidTheme",
    "class_defs",
    "render_legend",
    "render_legend_compact",
    "render_mermaid",
]


def __getattr__(name: str) -> object:
    return getattr(_mermaid, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_mermaid)))
