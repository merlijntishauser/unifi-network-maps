from __future__ import annotations

import os

import pytest

from tests.contract_helpers import assert_client_contract, assert_device_contract
from unifi_network_maps.adapters.config import Config
from unifi_network_maps.adapters.unifi import fetch_clients, fetch_devices

LIVE_FLAG = os.environ.get("UNIFI_CONTRACT_LIVE") == "1"


def _require_live() -> None:
    if not LIVE_FLAG:
        pytest.skip("Set UNIFI_CONTRACT_LIVE=1 to run live UniFi contract tests.")


def _load_live_config() -> Config:
    try:
        return Config.from_env()
    except ValueError as exc:
        pytest.skip(f"Missing UniFi env config: {exc}")
        raise


def _as_dict(obj: object) -> dict:
    if isinstance(obj, dict):
        return obj
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        data = to_dict()
        if isinstance(data, dict):
            return data
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


def _assert_device_list_contract(devices: list[object]) -> None:
    if not devices:
        raise AssertionError("Live device list is empty")
    for device in devices[:20]:
        payload = _as_dict(device)
        if not payload:
            raise AssertionError("Device could not be coerced to dict")
        assert_device_contract(payload)


def _assert_client_list_contract(clients: list[object]) -> None:
    if not clients:
        raise AssertionError("Live client list is empty")
    for client in clients[:20]:
        payload = _as_dict(client)
        if not payload:
            raise AssertionError("Client could not be coerced to dict")
        assert_client_contract(payload)


def test_live_unifi_devices_contract():
    _require_live()
    config = _load_live_config()
    devices = list(fetch_devices(config, site=config.site, detailed=True))
    _assert_device_list_contract(devices)


def test_live_unifi_clients_contract():
    _require_live()
    config = _load_live_config()
    clients = list(fetch_clients(config, site=config.site))
    _assert_client_list_contract(clients)
