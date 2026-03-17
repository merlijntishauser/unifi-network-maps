"""Compatibility wrapper for moved markdown renderers."""

from __future__ import annotations

from unifi_topology.render import markdown as _markdown

render_device_port_details = _markdown.render_device_port_details
render_device_port_overview = _markdown.render_device_port_overview

__all__ = [
    "render_device_port_details",
    "render_device_port_overview",
]


def __getattr__(name: str) -> object:
    return getattr(_markdown, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_markdown)))
