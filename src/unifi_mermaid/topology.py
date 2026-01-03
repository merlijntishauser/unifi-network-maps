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
    port_table: list[PortInfo] = field(default_factory=list)
    poe_ports: dict[int, bool] = field(default_factory=dict)
    uplink: UplinkInfo | None = None
    last_uplink: UplinkInfo | None = None


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
    uplink: object | None
    last_uplink: object | None
    uplink_mac: object | None
    uplink_device_mac: object | None
    last_uplink_mac: object | None
    uplink_device_name: object | None
    uplink_remote_port: object | None


@dataclass(frozen=True)
class UplinkInfo:
    mac: str | None
    name: str | None
    port: int | None


@dataclass(frozen=True)
class PortInfo:
    port_idx: int | None
    name: str | None
    ifname: str | None
    port_poe: bool
    poe_enable: bool
    poe_good: bool
    poe_power: float | None


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


def _as_int(value: object | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _coerce_port_table(device: DeviceLike) -> list[PortInfo]:
    port_table = _get_attr(device, "port_table") or []
    result: list[PortInfo] = []
    for entry in port_table:
        if isinstance(entry, dict):
            port_idx = entry.get("port_idx") or entry.get("portIdx")
            name = entry.get("name")
            ifname = entry.get("ifname")
            port_poe = _as_bool(entry.get("port_poe"))
            poe_enable = _as_bool(entry.get("poe_enable"))
            poe_good = _as_bool(entry.get("poe_good"))
            poe_power = _as_float(entry.get("poe_power"))
        else:
            port_idx = _get_attr(entry, "port_idx") or _get_attr(entry, "portIdx")
            name = _get_attr(entry, "name")
            ifname = _get_attr(entry, "ifname")
            port_poe = _as_bool(_get_attr(entry, "port_poe"))
            poe_enable = _as_bool(_get_attr(entry, "poe_enable"))
            poe_good = _as_bool(_get_attr(entry, "poe_good"))
            poe_power = _as_float(_get_attr(entry, "poe_power"))
        result.append(
            PortInfo(
                port_idx=_as_int(port_idx),
                name=str(name) if isinstance(name, str) and name.strip() else None,
                ifname=str(ifname) if isinstance(ifname, str) and ifname.strip() else None,
                port_poe=port_poe,
                poe_enable=poe_enable,
                poe_good=poe_good,
                poe_power=poe_power,
            )
        )
    return result


def _poe_ports_from_device(device: DeviceLike) -> dict[int, bool]:
    port_table = _coerce_port_table(device)
    poe_ports: dict[int, bool] = {}
    for entry in port_table:
        if entry.port_idx is None:
            continue
        active = (
            entry.poe_enable or entry.port_poe or entry.poe_good or _as_float(entry.poe_power) > 0.0
        )
        poe_ports[int(entry.port_idx)] = active
    return poe_ports


def _device_field(device: object, name: str) -> object | None:
    if isinstance(device, dict):
        return device.get(name)
    return getattr(device, name, None)


def _parse_uplink(value: object | None) -> UplinkInfo | None:
    if value is None:
        return None
    if isinstance(value, dict):
        mac = value.get("uplink_mac") or value.get("uplink_device_mac")
        name = value.get("uplink_device_name") or value.get("uplink_name")
        port = _as_int(value.get("uplink_remote_port") or value.get("port_idx"))
    else:
        mac = _get_attr(value, "uplink_mac") or _get_attr(value, "uplink_device_mac")
        name = _get_attr(value, "uplink_device_name") or _get_attr(value, "uplink_name")
        port = _as_int(_get_attr(value, "uplink_remote_port") or _get_attr(value, "port_idx"))
    mac_value = str(mac).strip() if isinstance(mac, str) and mac.strip() else None
    name_value = str(name).strip() if isinstance(name, str) and name.strip() else None
    if mac_value is None and name_value is None and port is None:
        return None
    return UplinkInfo(mac=mac_value, name=name_value, port=port)


def _uplink_info(device: DeviceLike) -> tuple[UplinkInfo | None, UplinkInfo | None]:
    uplink = _parse_uplink(_device_field(device, "uplink"))
    last_uplink = _parse_uplink(_device_field(device, "last_uplink"))

    if uplink is None:
        mac = _device_field(device, "uplink_mac") or _device_field(device, "uplink_device_mac")
        name = _device_field(device, "uplink_device_name")
        port = _as_int(_device_field(device, "uplink_remote_port"))
        uplink = _parse_uplink(
            {"uplink_mac": mac, "uplink_device_name": name, "uplink_remote_port": port}
        )

    if last_uplink is None:
        mac = _device_field(device, "last_uplink_mac")
        last_uplink = _parse_uplink({"uplink_mac": mac})

    return uplink, last_uplink


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
    uplink, last_uplink = _uplink_info(device)
    if lldp_info is None:
        if uplink or last_uplink:
            logger.warning("Device %s missing LLDP info; using uplink fallback", name)
            lldp_info = []
        else:
            raise ValueError(f"Device {name} missing LLDP info")

    coerced_lldp = [coerce_lldp(entry) for entry in lldp_info]
    port_table = _coerce_port_table(device)
    poe_ports = _poe_ports_from_device(device)

    return Device(
        name=str(name),
        model_name=str(model_name or ""),
        mac=str(mac),
        ip=str(ip or ""),
        type=str(dev_type or ""),
        lldp_info=coerced_lldp,
        port_table=port_table,
        poe_ports=poe_ports,
        uplink=uplink,
        last_uplink=last_uplink,
    )


def normalize_devices(devices: Iterable[DeviceLike]) -> list[Device]:
    return [coerce_device(device) for device in devices]


def classify_device_type(device: Device) -> str:
    value = device.type.strip().lower()
    if not value:
        name = device.name.strip().lower()
        if "gateway" in name or name.startswith("gw"):
            return "gateway"
        if "switch" in name:
            return "switch"
        if "ap" in name:
            return "ap"
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
        for neighbor in sorted(adjacency.get(current, set())):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)

    tree_edges: list[Edge] = []
    for child in sorted(parent):
        parent_name = parent[child]
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
                label = f"{device_name}: Port {uplink_port} <-> {name}"
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
    ordered_devices = sorted(devices, key=lambda item: (item.name.lower(), item.mac.lower()))
    index = build_device_index(ordered_devices)
    device_by_name = {device.name: device for device in ordered_devices}
    pairs: list[tuple[str, str]] = []
    seen: set[frozenset[str]] = set()
    port_map: dict[tuple[str, str], str] = {}
    poe_map: dict[tuple[str, str], bool] = {}
    devices_with_lldp_edges: set[str] = set()

    for device in ordered_devices:
        poe_ports = device.poe_ports
        for entry in sorted(
            device.lldp_info,
            key=lambda item: (
                _normalize_mac(item.chassis_id),
                str(item.port_id or ""),
                str(item.port_desc or ""),
            ),
        ):
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
            devices_with_lldp_edges.add(device.name)

    for device in ordered_devices:
        if device.name in devices_with_lldp_edges:
            continue
        uplink = device.uplink or device.last_uplink
        uplink_name = None
        if uplink and uplink.mac:
            uplink_name = index.get(_normalize_mac(uplink.mac))
        if not uplink_name and uplink and uplink.name:
            uplink_name = uplink.name
        if not uplink_name and not only_unifi and uplink and uplink.mac:
            uplink_name = uplink.mac
        if not uplink_name:
            continue
        if only_unifi and uplink_name not in device_by_name:
            continue
        key = frozenset({device.name, uplink_name})
        if key in seen:
            continue
        poe = False
        if uplink and uplink.port is not None:
            if include_ports:
                port_map[(uplink_name, device.name)] = f"Port {uplink.port}"
            uplink_device = device_by_name.get(uplink_name)
            if uplink_device and uplink.port in uplink_device.poe_ports:
                poe = uplink_device.poe_ports[uplink.port]
        pairs.append((uplink_name, device.name))
        seen.add(key)
        if poe:
            poe_map[(uplink_name, device.name)] = poe

    edges: list[Edge] = []
    for left, right in pairs:
        if include_ports:
            left_label = port_map.get((left, right))
            right_label = port_map.get((right, left))
            if left_label is None and right_label is not None:
                left, right = right, left
            elif left_label and right_label:
                left_device = device_by_name.get(left)
                right_device = device_by_name.get(right)
                if left_device and right_device:
                    type_rank = {"gateway": 0, "switch": 1, "ap": 2, "other": 3}
                    left_rank = type_rank.get(classify_device_type(left_device), 3)
                    right_rank = type_rank.get(classify_device_type(right_device), 3)
                    if (left_rank, left.lower()) > (right_rank, right.lower()):
                        left, right = right, left
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
