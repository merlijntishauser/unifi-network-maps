"""Compatibility wrapper for moved port aggregation helpers."""

from __future__ import annotations

from unifi_topology.render import _device_ports_aggregate as _aggregate

aggregate_base_groups = _aggregate.aggregate_base_groups
aggregate_ports = _aggregate.aggregate_ports
aggregate_sort_key = _aggregate.aggregate_sort_key
extend_singleton_groups = _aggregate.extend_singleton_groups
format_aggregate_label = _aggregate.format_aggregate_label
looks_like_lag = _aggregate.looks_like_lag
port_index = _aggregate.port_index

__all__ = [
    "aggregate_base_groups",
    "aggregate_ports",
    "aggregate_sort_key",
    "extend_singleton_groups",
    "format_aggregate_label",
    "looks_like_lag",
    "port_index",
]


def __getattr__(name: str) -> object:
    return getattr(_aggregate, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_aggregate)))
