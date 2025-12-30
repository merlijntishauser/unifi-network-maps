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
    local_port_name: str | None = None
    local_port_idx: int | None = None


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
    port_desc = (
        _get_attr(entry, "port_desc")
        or _get_attr(entry, "portDesc")
        or _get_attr(entry, "port_descr")
        or _get_attr(entry, "portDescr")
    )
    local_port_name = _get_attr(entry, "local_port_name") or _get_attr(entry, "localPortName")
    local_port_idx = _get_attr(entry, "local_port_idx") or _get_attr(entry, "localPortIdx")
    if not chassis_id or not port_id:
        raise ValueError("LLDP entry missing chassis_id or port_id")
    return LLDPEntry(
        chassis_id=str(chassis_id),
        port_id=str(port_id),
        port_desc=str(port_desc) if port_desc else None,
        local_port_name=str(local_port_name) if local_port_name else None,
        local_port_idx=int(local_port_idx) if local_port_idx is not None else None,
    )


def _looks_like_mac(value: str | None) -> bool:
    if not value:
        return False
    cleaned = value.strip().lower()
    if cleaned.count(":") == 5:
        return all(
            len(part) == 2 and all(ch in "0123456789abcdef" for ch in part)
            for part in cleaned.split(":")
        )
    return False


def _local_port_label(entry: LLDPEntry) -> str | None:
    if entry.local_port_name:
        return entry.local_port_name
    if entry.local_port_idx is not None:
        return f"Port {entry.local_port_idx}"
    if entry.port_desc and not _looks_like_mac(entry.port_desc):
        return entry.port_desc
    if entry.port_id and not _looks_like_mac(entry.port_id):
        return entry.port_id
    return None


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


def build_tree_edges_by_topology(edges: Iterable[Edge], gateways: list[str]) -> list[Edge]:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.left, set()).add(edge.right)
        adjacency.setdefault(edge.right, set()).add(edge.left)

    if not gateways:
        return []

    label_map: dict[frozenset[str], str | None] = {}
    for edge in edges:
        label_map[frozenset({edge.left, edge.right})] = edge.label

    visited: set[str] = set()
    parent: dict[str, str] = {}
    queue: list[str] = []

    for gateway in gateways:
        if gateway in adjacency:
            visited.add(gateway)
            queue.append(gateway)

    while queue:
        current = queue.pop(0)
        for neighbor in adjacency.get(current, set()):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)

    tree_edges: list[Edge] = []
    for child, parent_name in parent.items():
        label = label_map.get(frozenset({child, parent_name}))
        tree_edges.append(Edge(left=parent_name, right=child, label=label))

    return tree_edges


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
    pairs: list[tuple[str, str]] = []
    seen: set[frozenset[str]] = set()
    port_map: dict[tuple[str, str], str] = {}

    for raw_device in devices:
        device = coerce_device(raw_device)
        for entry in device.lldp_info:
            neighbor_mac = _normalize_mac(entry.chassis_id)
            neighbor_name = index.get(neighbor_mac)
            if neighbor_name is None:
                if only_unifi:
                    continue
                neighbor_name = entry.chassis_id

            label = _local_port_label(entry)
            if label:
                port_map[(device.name, neighbor_name)] = label

            key = frozenset({device.name, neighbor_name})
            if key in seen:
                continue

            pairs.append((device.name, neighbor_name))
            seen.add(key)

    edges: list[Edge] = []
    for left, right in pairs:
        label = None
        if include_ports:
            left_label = port_map.get((left, right))
            right_label = port_map.get((right, left))
            if left_label and right_label:
                label = f"{left}: {left_label} <-> {right}: {right_label}"
            elif left_label:
                label = f"{left}: {left_label} <-> {right}: ?"
            elif right_label:
                label = f"{left}: ? <-> {right}: {right_label}"
        edges.append(Edge(left=left, right=right, label=label))

    logger.info("Built %d unique edges", len(edges))
    return edges
