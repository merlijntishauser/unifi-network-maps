"""Load mock UniFi data from JSON fixtures."""

from __future__ import annotations

import json

from .paths import resolve_mock_data_path


def _as_list(value: object, name: str) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"Mock data field '{name}' must be a list")


def load_mock_data(path: str) -> tuple[list[object], list[object]]:
    resolved = resolve_mock_data_path(path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Mock data must be a JSON object")
    devices = _as_list(payload.get("devices"), "devices")
    clients = _as_list(payload.get("clients"), "clients")
    return devices, clients


def load_mock_payload(path: str) -> dict[str, list[object] | list[dict[str, object]]]:
    resolved = resolve_mock_data_path(path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Mock data must be a JSON object")
    devices = _as_list(payload.get("devices"), "devices")
    clients = _as_list(payload.get("clients"), "clients")
    networks = _as_list(payload.get("networks"), "networks")
    vlan_info = _as_list(payload.get("vlan_info"), "vlan_info")
    return {
        "devices": devices,
        "clients": clients,
        "networks": networks,
        "vlan_info": vlan_info,
    }
