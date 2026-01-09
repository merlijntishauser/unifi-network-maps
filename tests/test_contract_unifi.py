from __future__ import annotations

from pathlib import Path

from tests.contract_helpers import (
    assert_client_contract,
    assert_device_contract,
    load_fixture,
)
from unifi_network_maps.io.mock_data import load_mock_data
from unifi_network_maps.model.topology import (
    build_client_edges,
    build_client_port_map,
    build_device_index,
    build_edges,
    normalize_devices,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_devices_fixture() -> list[object]:
    return load_fixture(str(FIXTURES_DIR / "unifi_devices.json"), "devices")


def _load_clients_fixture() -> list[object]:
    return load_fixture(str(FIXTURES_DIR / "unifi_clients.json"), "clients")


def test_unifi_device_fixture_contract():
    devices = _load_devices_fixture()
    assert devices
    for device in devices:
        assert_device_contract(device)


def test_unifi_client_fixture_contract():
    clients = _load_clients_fixture()
    assert clients
    for client in clients:
        assert_client_contract(client)


def test_unifi_fixture_normalization_contract():
    devices = _load_devices_fixture()
    normalized = normalize_devices(devices)
    edges = build_edges(normalized, include_ports=True, only_unifi=False)
    assert normalized
    assert edges


def test_unifi_fixture_client_edges_contract():
    devices = normalize_devices(_load_devices_fixture())
    clients = _load_clients_fixture()
    edges = build_client_edges(
        clients,
        build_device_index(devices),
        include_ports=True,
        client_mode="all",
    )
    assert any(edge.label and "Port 5" in edge.label for edge in edges)


def test_unifi_fixture_client_ports_contract():
    devices = normalize_devices(_load_devices_fixture())
    clients = _load_clients_fixture()
    client_ports = build_client_port_map(devices, clients, client_mode="all")
    rows = client_ports.get("Core Switch", [])
    assert (5, "Desk PC") in rows


def test_mock_data_fixture_contract():
    devices, clients = load_mock_data(str(Path("examples/mock_data.json")))
    normalized = normalize_devices(devices)
    edges = build_edges(normalized, include_ports=True, only_unifi=False)
    assert normalized
    assert edges
    assert clients
