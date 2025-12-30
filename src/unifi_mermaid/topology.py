"""Topology normalization and edge construction."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

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
    poe_ports: dict[int, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    left: str
    right: str
    label: str | None = None
    poe: bool = False


class DeviceLike(Protocol):
    name: str | None
    model_name: str | None
    model: str | None
    mac: str | None
    ip: str | None
    ip_address: str | None
    type: str | None
    device_type: str | None
    lldp_info: object | None
    lldp: object | None
    port_table: object | None


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
    number = None
    name = None
    desc = None

    if entry.local_port_idx is not None:
        number = entry.local_port_idx
    if entry.local_port_name:
        name = _normalize_port_label(entry.local_port_name)
    if entry.port_desc and not _looks_like_mac(entry.port_desc):
        desc = entry.port_desc.strip()
    if entry.port_id and not _looks_like_mac(entry.port_id):
        if name is None:
            name = _normalize_port_label(entry.port_id)

    if number is None:
        number = _extract_port_number(name)
    if number is None:
        number = _extract_port_number(desc)

    if number is not None and desc:
        return f"Port {number} ({desc})"
    if number is not None:
        return f"Port {number}"
    if name:
        return name
    if desc:
        return desc
    return None


def _as_bool(value: object | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _as_float(value: object | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _poe_ports_from_device(device: DeviceLike) -> dict[int, bool]:
    port_table = _get_attr(device, "port_table") or []
    poe_ports: dict[int, bool] = {}
    for entry in port_table:
        port_idx = _get_attr(entry, "port_idx") or _get_attr(entry, "portIdx")
        if port_idx is None and isinstance(entry, dict):
            port_idx = entry.get("port_idx") or entry.get("portIdx")
        if port_idx is None:
            continue
        poe_enable = _get_attr(entry, "poe_enable") or (
            entry.get("poe_enable") if isinstance(entry, dict) else None
        )
        port_poe = _get_attr(entry, "port_poe") or (
            entry.get("port_poe") if isinstance(entry, dict) else None
        )
        poe_good = _get_attr(entry, "poe_good") or (
            entry.get("poe_good") if isinstance(entry, dict) else None
        )
        poe_power = _get_attr(entry, "poe_power") or (
            entry.get("poe_power") if isinstance(entry, dict) else None
        )

        active = (
            _as_bool(poe_enable)
            or _as_bool(port_poe)
            or _as_bool(poe_good)
            or _as_float(poe_power) > 0.0
        )
        poe_ports[int(port_idx)] = active
    return poe_ports


def _extract_port_number(label: str | None) -> int | None:
    if not label:
        return None
    match = re.search(r"(?:^|[^0-9])(?:port|eth)\s*([0-9]+)", label.strip(), re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _normalize_port_label(label: str) -> str:
    trimmed = label.strip()
    number = _extract_port_number(trimmed)
    if number is not None:
        return f"Port {number}"
    return trimmed


def _compose_edge_label(left: str, right: str, port_map: dict[tuple[str, str], str]) -> str | None:
    left_label = port_map.get((left, right))
    right_label = port_map.get((right, left))
    if left_label and right_label:
        return f"{left}: {left_label} <-> {right}: {right_label}"
    if left_label:
        return f"{left}: {left_label} <-> {right}: ?"
    if right_label:
        return f"{left}: ? <-> {right}: {right_label}"
    return None


def coerce_device(device: DeviceLike) -> Device:
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
    poe_ports = _poe_ports_from_device(device)

    return Device(
        name=str(name),
        model_name=str(model_name or ""),
        mac=str(mac),
        ip=str(ip or ""),
        type=str(dev_type or ""),
        lldp_info=coerced_lldp,
        poe_ports=poe_ports,
    )


def normalize_devices(devices: Iterable[DeviceLike]) -> list[Device]:
    return [coerce_device(device) for device in devices]


def classify_device_type(device: Device) -> str:
    value = device.type.strip().lower()
    if value in {"gateway", "ugw", "usg", "ux", "udm", "udr"}:
        return "gateway"
    if value in {"switch", "usw"}:
        return "switch"
    if value in {"uap", "ap"} or "ap" in value:
        return "ap"
    return "other"


def group_devices_by_type(devices: Iterable[Device]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"gateway": [], "switch": [], "ap": [], "other": []}
    for device in devices:
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

    edge_map: dict[frozenset[str], Edge] = {}
    for edge in edges:
        edge_map[frozenset({edge.left, edge.right})] = edge

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
        original = edge_map.get(frozenset({child, parent_name}))
        if original is None:
            tree_edges.append(Edge(left=parent_name, right=child))
        else:
            tree_edges.append(
                Edge(left=parent_name, right=child, label=original.label, poe=original.poe)
            )

    return tree_edges


def build_device_index(devices: Iterable[Device]) -> dict[str, str]:
    index: dict[str, str] = {}
    for device in devices:
        index[_normalize_mac(device.mac)] = device.name
    return index


def build_edges(
    devices: Iterable[Device],
    *,
    include_ports: bool = False,
    only_unifi: bool = True,
) -> list[Edge]:
    index = build_device_index(devices)
    pairs: list[tuple[str, str]] = []
    seen: set[frozenset[str]] = set()
    port_map: dict[tuple[str, str], str] = {}
    poe_map: dict[tuple[str, str], bool] = {}

    for device in devices:
        poe_ports = device.poe_ports
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
            if entry.local_port_idx is not None and entry.local_port_idx in poe_ports:
                poe_map[(device.name, neighbor_name)] = poe_ports[entry.local_port_idx]

            key = frozenset({device.name, neighbor_name})
            if key in seen:
                continue

            pairs.append((device.name, neighbor_name))
            seen.add(key)

    edges: list[Edge] = []
    for left, right in pairs:
        poe = poe_map.get((left, right), False) or poe_map.get((right, left), False)
        label = _compose_edge_label(left, right, port_map) if include_ports else None
        edges.append(Edge(left=left, right=right, label=label, poe=poe))

    logger.info("Built %d unique edges", len(edges))
    return edges


@dataclass(frozen=True)
class TopologyResult:
    raw_edges: list[Edge]
    tree_edges: list[Edge]


def build_topology(
    devices: Iterable[Device],
    *,
    include_ports: bool,
    only_unifi: bool,
    gateways: list[str],
) -> TopologyResult:
    raw_edges = build_edges(devices, include_ports=include_ports, only_unifi=only_unifi)
    tree_edges = build_tree_edges_by_topology(raw_edges, gateways)
    return TopologyResult(raw_edges=raw_edges, tree_edges=tree_edges)
