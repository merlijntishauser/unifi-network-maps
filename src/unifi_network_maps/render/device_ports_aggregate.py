"""Port aggregation (LAG) detection and formatting."""

from __future__ import annotations

from collections import defaultdict

from ..model.ports import extract_port_number
from ..model.topology import PortInfo


def looks_like_lag(port: PortInfo) -> bool:
    name = (port.name or "").lower()
    ifname = (port.ifname or "").lower()
    return "lag" in name or "lag" in ifname or "aggregate" in name


def aggregate_base_groups(port_table: list[PortInfo]) -> dict[str, list[PortInfo]]:
    groups: dict[str, list[PortInfo]] = defaultdict(list)
    for port in port_table:
        if port.aggregation_group:
            groups[str(port.aggregation_group)].append(port)
            continue
        if looks_like_lag(port):
            if port.port_idx is not None:
                groups[f"lag-{port.port_idx}"].append(port)
    return groups


def _find_lag_neighbors(
    lone_port: PortInfo,
    port_by_idx: dict[int, PortInfo],
) -> list[PortInfo]:
    port_idx = lone_port.port_idx
    if port_idx is None:
        return []
    candidates: list[PortInfo] = []
    for neighbor_idx in (port_idx - 1, port_idx + 1):
        port = port_by_idx.get(neighbor_idx)
        if port and not port.aggregation_group and port.speed == lone_port.speed:
            candidates.append(port)
    return candidates


def extend_singleton_groups(
    groups: dict[str, list[PortInfo]],
    port_table: list[PortInfo],
) -> None:
    if not groups:
        return
    port_by_idx: dict[int, PortInfo] = {
        port.port_idx: port for port in port_table if port.port_idx is not None
    }
    for group_id, group_ports in list(groups.items()):
        if len(group_ports) != 1:
            continue
        lone_port = group_ports[0]
        if not looks_like_lag(lone_port):
            continue
        candidates = _find_lag_neighbors(lone_port, port_by_idx)
        if candidates:
            groups[group_id].extend(candidates)


def aggregate_ports(port_table: list[PortInfo]) -> dict[str, list[PortInfo]]:
    """Group ports by aggregation/LAG membership."""
    groups = aggregate_base_groups(port_table)
    extend_singleton_groups(groups, port_table)
    return groups


def aggregate_sort_key(group_ports: list[PortInfo]) -> int:
    ports = sorted([int(p.port_idx) for p in group_ports if p.port_idx is not None])
    return ports[0] if ports else 10_000


def format_aggregate_label(group_ports: list[PortInfo]) -> str:
    ports = sorted([int(p.port_idx) for p in group_ports if p.port_idx is not None])
    if ports:
        if len(ports) == 1:
            return f"Port {ports[0]} (LAG)"
        if ports == list(range(ports[0], ports[-1] + 1)):
            return f"Port {ports[0]}-{ports[-1]} (LAG)"
        return "Ports " + "+".join(str(port) for port in ports) + " (LAG)"
    return "Aggregated ports"


def port_index(port_idx: int | None, name: str | None) -> int | None:
    if port_idx is not None:
        return port_idx
    if name:
        return extract_port_number(name)
    return None
