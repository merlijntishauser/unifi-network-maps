"""Topology normalization and edge construction."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLDPEntry:
    chassis_id: str
    port_id: str
    port_desc: str | None = None


@dataclass(frozen=True)
class Device:
    name: str
    model_name: str
    mac: str
    ip: str
    type: str
    lldp_info: list[LLDPEntry]


@dataclass(frozen=True)
class Edge:
    left: str
    right: str
    label: str | None = None


def _get_attr(obj: object, name: str) -> object | None:
    return getattr(obj, name, None)


def _normalize_mac(value: str) -> str:
    return value.strip().lower()


def _coerce_lldp(entry: object) -> LLDPEntry:
    chassis_id = _get_attr(entry, "chassis_id") or _get_attr(entry, "chassisId")
    port_id = _get_attr(entry, "port_id") or _get_attr(entry, "portId")
    port_desc = _get_attr(entry, "port_desc") or _get_attr(entry, "portDesc")
    if not chassis_id or not port_id:
        raise ValueError("LLDP entry missing chassis_id or port_id")
    return LLDPEntry(
        chassis_id=str(chassis_id),
        port_id=str(port_id),
        port_desc=str(port_desc) if port_desc else None,
    )


def coerce_device(device: object) -> Device:
    name = _get_attr(device, "name")
    model_name = _get_attr(device, "model_name") or _get_attr(device, "model")
    mac = _get_attr(device, "mac")
    ip = _get_attr(device, "ip") or _get_attr(device, "ip_address")
    dev_type = _get_attr(device, "type") or _get_attr(device, "device_type")
    lldp_info = _get_attr(device, "lldp_info")
    if lldp_info is None:
        lldp_info = _get_attr(device, "lldp")

    if not name or not mac:
        raise ValueError("Device missing name or mac")
    if lldp_info is None:
        raise ValueError(f"Device {name} missing LLDP info")

    coerced_lldp = [_coerce_lldp(entry) for entry in lldp_info]

    return Device(
        name=str(name),
        model_name=str(model_name or ""),
        mac=str(mac),
        ip=str(ip or ""),
        type=str(dev_type or ""),
        lldp_info=coerced_lldp,
    )


def classify_device_type(device: Device) -> str:
    value = device.type.strip().lower()
    if value in {"gateway", "ugw", "usg", "ux", "udm", "udr"}:
        return "gateway"
    if value in {"switch", "usw"}:
        return "switch"
    if value in {"uap", "ap"} or "ap" in value:
        return "ap"
    return "other"


def group_devices_by_type(devices: Iterable[object]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"gateway": [], "switch": [], "ap": [], "other": []}
    for raw_device in devices:
        device = coerce_device(raw_device)
        group = classify_device_type(device)
        groups[group].append(device.name)
    return groups


def build_rank_edges_by_topology(
    edges: Iterable[Edge], gateways: list[str]
) -> list[tuple[str, str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.left, set()).add(edge.right)
        adjacency.setdefault(edge.right, set()).add(edge.left)

    if not gateways:
        return []

    distances: dict[str, int] = {}
    queue: list[str] = []
    for gateway in gateways:
        if gateway in adjacency:
            distances[gateway] = 0
            queue.append(gateway)

    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, set()):
            if neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)

    levels: dict[int, list[str]] = {}
    for node, distance in distances.items():
        levels.setdefault(distance, []).append(node)

    rank_edges: list[tuple[str, str]] = []
    for level in sorted(levels.keys()):
        next_level = level + 1
        if next_level not in levels:
            continue
        for upper_node in levels[level]:
            for lower_node in levels[next_level]:
                rank_edges.append((upper_node, lower_node))

    return rank_edges


def build_device_index(devices: Iterable[object]) -> dict[str, str]:
    index: dict[str, str] = {}
    for device in devices:
        normalized = coerce_device(device)
        index[_normalize_mac(normalized.mac)] = normalized.name
    return index


def build_edges(
    devices: Iterable[object],
    *,
    include_ports: bool = False,
    only_unifi: bool = True,
) -> list[Edge]:
    index = build_device_index(devices)
    edges: list[Edge] = []
    seen: set[frozenset[str]] = set()

    for raw_device in devices:
        device = coerce_device(raw_device)
        for entry in device.lldp_info:
            neighbor_mac = _normalize_mac(entry.chassis_id)
            neighbor_name = index.get(neighbor_mac)
            if neighbor_name is None:
                if only_unifi:
                    continue
                neighbor_name = entry.chassis_id

            key = frozenset({device.name, neighbor_name})
            if key in seen:
                continue

            label = None
            if include_ports:
                label = entry.port_desc or entry.port_id

            edges.append(Edge(left=device.name, right=neighbor_name, label=label))
            seen.add(key)

    logger.info("Built %d unique edges", len(edges))
    return edges
