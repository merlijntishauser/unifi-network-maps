"""Compatibility wrapper for moved device summary helpers."""

from __future__ import annotations

from unifi_topology.render import _device_summary as _device_summary

poe_summary = _device_summary.poe_summary
port_summary = _device_summary.port_summary
uplink_summary = _device_summary.uplink_summary

__all__ = [
    "poe_summary",
    "port_summary",
    "uplink_summary",
]


def __getattr__(name: str) -> object:
    return getattr(_device_summary, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_device_summary)))
