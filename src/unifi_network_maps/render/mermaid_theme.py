"""Compatibility wrapper for moved Mermaid theme helpers."""

from __future__ import annotations

from unifi_topology.render import mermaid_theme as _mermaid_theme

DEFAULT_THEME = _mermaid_theme.DEFAULT_THEME
MermaidTheme = _mermaid_theme.MermaidTheme
class_defs = _mermaid_theme.class_defs

__all__ = [
    "DEFAULT_THEME",
    "MermaidTheme",
    "class_defs",
]


def __getattr__(name: str) -> object:
    return getattr(_mermaid_theme, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_mermaid_theme)))
