"""Compatibility wrapper for moved LLDP markdown rendering."""

from __future__ import annotations

from unifi_topology.render import lldp as _lldp

render_lldp_md = _lldp.render_lldp_md

__all__ = ["render_lldp_md"]


def __getattr__(name: str) -> object:
    return getattr(_lldp, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_lldp)))
