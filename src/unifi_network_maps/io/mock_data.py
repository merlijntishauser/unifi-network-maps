"""Load mock UniFi data from JSON fixtures."""

from __future__ import annotations

import json
from pathlib import Path


def _as_list(value: object, name: str) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ValueError(f"Mock data field '{name}' must be a list")


def load_mock_data(path: str) -> tuple[list[object], list[object]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Mock data must be a JSON object")
    devices = _as_list(payload.get("devices"), "devices")
    clients = _as_list(payload.get("clients"), "clients")
    return devices, clients
