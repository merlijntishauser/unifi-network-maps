"""Topology normalization and edge construction."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable, Optional

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


def _get_attr(obj: object, name: str) -> Optional[object]:
    return getattr(obj, name, None)


def _normalize_mac(value: str) -> str:
    return value.strip().lower()


def _coerce_lldp(entry: object) -> LLDPEntry:
    chassis_id = _get_attr(entry, "chassis_id") or _get_attr(entry, "chassisId")
    port_id = _get_attr(entry, "port_id") or _get_attr(entry, "portId")
    port_desc = _get_attr(entry, "port_desc") or _get_attr(entry, "portDesc")
    if not chassis_id or not port_id:
        raise ValueError("LLDP entry missing chassis_id or port_id")
    return LLDPEntry(chassis_id=str(chassis_id), port_id=str(port_id), port_desc=str(port_desc) if port_desc else None)


def coerce_device(device: object) -> Device:
    name = _get_attr(device, "name")
    model_name = _get_attr(device, "model_name") or _get_attr(device, "model")
    mac = _get_attr(device, "mac")
    ip = _get_attr(device, "ip") or _get_attr(device, "ip_address")
    dev_type = _get_attr(device, "type") or _get_attr(device, "device_type")
    lldp_info = _get_attr(device, "lldp_info") or _get_attr(device, "lldp")

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
