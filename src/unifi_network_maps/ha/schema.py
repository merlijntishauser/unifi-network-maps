"""Home Assistant POC JSON schema helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..model.topology import Device, Edge, PortMap, build_client_port_map, build_port_map


@dataclass(frozen=True)
class HaSchema:
    devices: list[dict[str, Any]]
    ports: list[dict[str, Any]]
    links: list[dict[str, Any]]
    clients: list[dict[str, Any]]


def _device_id(device: Device) -> str:
    return device.mac or device.name


def _port_id(device_id: str, port_label: str) -> str:
    return f"{device_id}:{port_label}"


def _port_label_from_map(port_map: PortMap, device: Device, neighbor: str | None) -> str | None:
    if neighbor is None:
        return None
    return port_map.get((device.name, neighbor))


def _client_records(
    devices: list[Device],
    clients: list[object] | None,
    *,
    client_mode: str,
) -> list[dict[str, Any]]:
    if not clients:
        return []
    client_port_map = build_client_port_map(devices, clients, client_mode=client_mode)
    records: list[dict[str, Any]] = []
    for device in devices:
        device_id = _device_id(device)
        for port_idx, client_name in client_port_map.get(device.name, []):
            port_label = f"Port {port_idx}"
            records.append(
                {
                    "id": f"{device_id}:{port_label}:{client_name}",
                    "name": client_name,
                    "mac": None,
                    "connected_port": _port_id(device_id, port_label),
                    "wired": True,
                }
            )
    return records


def build_ha_schema(
    devices: list[Device],
    edges: list[Edge],
    *,
    clients: list[object] | None,
    client_mode: str,
) -> HaSchema:
    port_map = build_port_map(devices, only_unifi=False)
    return HaSchema(
        devices=_device_payloads(devices),
        ports=_port_payloads(devices),
        links=_link_payloads(edges, devices, port_map),
        clients=_client_records(devices, clients, client_mode=client_mode),
    )


def _device_payloads(devices: list[Device]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for device in devices:
        payloads.append(_device_payload(device))
    return payloads


def _device_payload(device: Device) -> dict[str, Any]:
    return {
        "id": _device_id(device),
        "name": device.name,
        "type": device.type,
        "model": device.model_name or device.model,
        "ip": device.ip,
        "mac": device.mac,
    }


def _port_payloads(devices: list[Device]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for device in devices:
        payloads.extend(_device_ports_payload(device))
    return payloads


def _device_ports_payload(device: Device) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    device_id = _device_id(device)
    for port in device.port_table:
        if port.port_idx is None:
            continue
        port_label = port.name or f"Port {port.port_idx}"
        payloads.append(
            {
                "id": _port_id(device_id, port_label),
                "device_id": device_id,
                "name": port_label,
                "poe_status": "active" if (port.poe_power or 0) > 0 else "inactive",
                "poe_power_w": round(port.poe_power or 0.0, 2),
                "speed": port.speed,
            }
        )
    return payloads


def _link_payloads(
    edges: list[Edge],
    devices: list[Device],
    port_map: PortMap,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for edge in edges:
        payloads.append(_link_payload(edge, devices, port_map))
    return payloads


def _link_payload(
    edge: Edge,
    devices: list[Device],
    port_map: PortMap,
) -> dict[str, Any]:
    left = next((device for device in devices if device.name == edge.left), None)
    right = next((device for device in devices if device.name == edge.right), None)
    left_id = _device_id(left) if left else edge.left
    right_id = _device_id(right) if right else edge.right
    left_port = _port_label_from_map(port_map, left, edge.right) if left else None
    right_port = _port_label_from_map(port_map, right, edge.left) if right else None
    return {
        "id": f"{left_id}:{right_id}",
        "left_device_id": left_id,
        "right_device_id": right_id,
        "left_port_id": _port_id(left_id, left_port) if left_port else None,
        "right_port_id": _port_id(right_id, right_port) if right_port else None,
        "poe": edge.poe,
    }
