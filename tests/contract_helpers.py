from __future__ import annotations

import json
from pathlib import Path


def load_fixture(path: str, key: str) -> list[object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("Fixture payload must be an object")
    value = payload.get(key)
    if not isinstance(value, list):
        raise AssertionError(f"Fixture '{key}' must be a list")
    return value


def assert_lldp_entry_contract(entry: object) -> None:
    if not isinstance(entry, dict):
        raise AssertionError("LLDP entry must be a dict")
    chassis_id = entry.get("chassis_id") or entry.get("chassisId")
    port_id = entry.get("port_id") or entry.get("portId")
    if not isinstance(chassis_id, str) or not chassis_id.strip():
        raise AssertionError("LLDP entry missing chassis_id")
    if not isinstance(port_id, str) or not port_id.strip():
        raise AssertionError("LLDP entry missing port_id")


def assert_device_contract(device: object) -> None:
    if not isinstance(device, dict):
        raise AssertionError("Device must be a dict")
    name = device.get("name")
    mac = device.get("mac")
    if not isinstance(name, str) or not name.strip():
        raise AssertionError("Device missing name")
    if not isinstance(mac, str) or not mac.strip():
        raise AssertionError("Device missing mac")
    lldp_info = device.get("lldp_info") or device.get("lldp") or []
    if not isinstance(lldp_info, list):
        raise AssertionError("Device lldp_info must be a list")
    for entry in lldp_info:
        assert_lldp_entry_contract(entry)
    port_table = device.get("port_table") or []
    if not isinstance(port_table, list):
        raise AssertionError("Device port_table must be a list")


def _client_uplink_mac(client: dict) -> str | None:
    for key in ("ap_mac", "sw_mac", "uplink_mac", "uplink_device_mac", "last_uplink_mac"):
        value = client.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    uplink = client.get("uplink")
    if isinstance(uplink, dict):
        value = uplink.get("uplink_mac") or uplink.get("uplink_device_mac")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def assert_client_contract(client: object) -> None:
    if not isinstance(client, dict):
        raise AssertionError("Client must be a dict")
    name = client.get("name") or client.get("hostname") or client.get("mac")
    if not isinstance(name, str) or not name.strip():
        raise AssertionError("Client missing display name")
    is_wired = client.get("is_wired")
    if not isinstance(is_wired, bool):
        raise AssertionError("Client missing is_wired boolean")
    if is_wired and not _client_uplink_mac(client):
        raise AssertionError("Wired client missing uplink mac")
