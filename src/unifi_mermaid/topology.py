"""Topology normalization and edge construction."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Protocol

from .labels import compose_port_label
from .lldp import LLDPEntry, coerce_lldp, local_port_label

logger = logging.getLogger(__name__)


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

    coerced_lldp = [coerce_lldp(entry) for entry in lldp_info]
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
    queue: deque[str] = deque()

    for gateway in gateways:
        if gateway in adjacency:
            visited.add(gateway)
            queue.append(gateway)

    while queue:
        current = queue.popleft()
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


def _client_field(client: object, name: str) -> object | None:
    if isinstance(client, dict):
        return client.get(name)
    return getattr(client, name, None)


def _client_display_name(client: object) -> str | None:
    for key in ("name", "hostname", "mac"):
        value = _client_field(client, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _client_uplink_mac(client: object) -> str | None:
    for key in ("ap_mac", "sw_mac", "uplink_mac", "uplink_device_mac", "last_uplink_mac"):
        value = _client_field(client, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("uplink", "last_uplink"):
        nested = _client_field(client, key)
        if isinstance(nested, dict):
            value = nested.get("uplink_mac") or nested.get("uplink_device_mac")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _client_uplink_port(client: object) -> int | None:
    for key in ("uplink_remote_port", "sw_port", "ap_port"):
        value = _client_field(client, key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    for key in ("uplink", "last_uplink"):
        nested = _client_field(client, key)
        if isinstance(nested, dict):
            value = nested.get("uplink_remote_port")
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
    return None


def _client_is_wired(client: object) -> bool:
    return bool(_client_field(client, "is_wired"))


def build_client_edges(
    clients: Iterable[object],
    device_index: dict[str, str],
    *,
    include_ports: bool = False,
) -> list[Edge]:
    edges: list[Edge] = []
    seen: set[tuple[str, str]] = set()
    for client in clients:
        if not _client_is_wired(client):
            continue
        name = _client_display_name(client)
        uplink_mac = _client_uplink_mac(client)
        if not name or not uplink_mac:
            continue
        device_name = device_index.get(_normalize_mac(uplink_mac))
        if not device_name:
            continue
        label = None
        if include_ports:
            uplink_port = _client_uplink_port(client)
            if uplink_port is not None:
                label = f"{device_name}: Port {uplink_port} <-> {name}: ?"
        key = (device_name, name)
        if key in seen:
            continue
        edges.append(Edge(left=device_name, right=name, label=label))
        seen.add(key)
    return edges


def build_node_type_map(
    devices: Iterable[Device], clients: Iterable[object] | None = None
) -> dict[str, str]:
    node_types: dict[str, str] = {}
    for device in devices:
        node_types[device.name] = classify_device_type(device)
    if clients:
        for client in clients:
            if not _client_is_wired(client):
                continue
            name = _client_display_name(client)
            if name:
                node_types[name] = "client"
    return node_types


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

            label = local_port_label(entry)
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
        label = compose_port_label(left, right, port_map) if include_ports else None
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
