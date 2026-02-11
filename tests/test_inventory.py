"""Tests for device inventory model."""

from unifi_network_maps.model.inventory import (
    DeviceInfo,
    build_client_inventory,
    build_device_inventory,
)
from unifi_network_maps.model.topology import Device


def _device(
    name: str,
    ip: str,
    *,
    dtype: str = "usw",
    model_name: str = "Switch",
    mac: str = "aa:bb:cc:dd:ee:ff",
    version: str = "7.0.0",
) -> Device:
    return Device(
        name=name,
        model_name=model_name,
        model="US-24",
        mac=mac,
        ip=ip,
        type=dtype,
        lldp_info=[],
        version=version,
    )


def test_build_inventory_basic():
    devices = [_device("SW1", "192.168.1.10")]
    result = build_device_inventory(devices)
    assert len(result) == 1
    assert result[0].name == "SW1"
    assert result[0].ip == "192.168.1.10"
    assert result[0].hostname is None


def test_build_inventory_joins_hostnames():
    devices = [_device("SW1", "192.168.1.10")]
    hostnames = {"192.168.1.10": "sw1.local"}
    result = build_device_inventory(devices, hostnames)
    assert result[0].hostname == "sw1.local"


def test_build_inventory_missing_hostname():
    devices = [_device("SW1", "192.168.1.10")]
    hostnames = {"192.168.1.99": "other.local"}
    result = build_device_inventory(devices, hostnames)
    assert result[0].hostname is None


def test_build_inventory_sorted_by_ip():
    devices = [
        _device("SW2", "192.168.1.20"),
        _device("GW", "192.168.1.1", dtype="ugw", model_name="Gateway"),
        _device("SW1", "192.168.1.10"),
    ]
    result = build_device_inventory(devices)
    assert [d.ip for d in result] == ["192.168.1.1", "192.168.1.10", "192.168.1.20"]


def test_build_inventory_classifies_device_type():
    devices = [
        _device("GW", "192.168.1.1", dtype="ugw"),
        _device("AP1", "192.168.1.30", dtype="uap"),
        _device("SW1", "192.168.1.10", dtype="usw"),
    ]
    result = build_device_inventory(devices)
    types = {d.name: d.device_type for d in result}
    assert types["GW"] == "gateway"
    assert types["SW1"] == "switch"
    assert types["AP1"] == "ap"


def test_build_inventory_firmware():
    devices = [_device("SW1", "192.168.1.10", version="6.5.28")]
    result = build_device_inventory(devices)
    assert result[0].firmware == "6.5.28"


def test_build_inventory_empty():
    result = build_device_inventory([])
    assert result == []


def test_device_info_frozen():
    info = DeviceInfo(
        name="SW1",
        device_type="switch",
        model_name="Switch",
        ip="192.168.1.10",
        hostname=None,
        mac="aa:bb:cc:dd:ee:ff",
        firmware="7.0.0",
    )
    assert info.name == "SW1"
    try:
        info.name = "changed"  # type: ignore[misc]
        raise AssertionError("Should be frozen")
    except AttributeError:
        pass


# --- build_client_inventory tests ---


def test_build_client_inventory_basic():
    clients = [
        {
            "name": "Ring Doorbell",
            "ip": "192.168.1.50",
            "mac": "aa:bb:cc:00:11:22",
            "is_wired": True,
        },
    ]
    result = build_client_inventory(clients)
    assert len(result) == 1
    assert result[0].name == "Ring Doorbell"
    assert result[0].device_type == "camera"
    assert result[0].ip == "192.168.1.50"
    assert result[0].mac == "aa:bb:cc:00:11:22"
    assert result[0].firmware == ""


def test_build_client_inventory_sorted_by_ip():
    clients = [
        {"name": "Client B", "ip": "192.168.1.20", "mac": "aa:bb:cc:00:00:02", "is_wired": True},
        {"name": "Client A", "ip": "192.168.1.10", "mac": "aa:bb:cc:00:00:01", "is_wired": True},
    ]
    result = build_client_inventory(clients)
    assert [d.ip for d in result] == ["192.168.1.10", "192.168.1.20"]


def test_build_client_inventory_filters_by_client_mode():
    clients = [
        {
            "name": "Wired Client",
            "ip": "192.168.1.10",
            "mac": "aa:00:00:00:00:01",
            "is_wired": True,
        },
        {
            "name": "Wireless Client",
            "ip": "192.168.1.11",
            "mac": "aa:00:00:00:00:02",
            "is_wired": False,
        },
    ]
    result = build_client_inventory(clients, client_mode="wired")
    assert len(result) == 1
    assert result[0].name == "Wired Client"


def test_build_client_inventory_joins_hostnames():
    clients = [
        {"name": "My Camera", "ip": "192.168.1.50", "mac": "aa:00:00:00:00:01", "is_wired": True},
    ]
    hostnames = {"192.168.1.50": "camera.local"}
    result = build_client_inventory(clients, hostnames)
    assert result[0].hostname == "camera.local"


def test_build_client_inventory_missing_ip():
    clients = [
        {"name": "No IP Client", "mac": "aa:00:00:00:00:01", "is_wired": True},
    ]
    result = build_client_inventory(clients)
    assert len(result) == 1
    assert result[0].ip == ""


def test_build_client_inventory_empty():
    result = build_client_inventory([])
    assert result == []


def test_build_client_inventory_model_from_ucore():
    clients = [
        {
            "name": "G4 Doorbell",
            "ip": "192.168.1.60",
            "mac": "aa:00:00:00:00:01",
            "is_wired": True,
            "unifi_device_info_from_ucore": {
                "computed_model": "G4 Doorbell Pro",
                "product_line": "protect",
            },
        },
    ]
    result = build_client_inventory(clients)
    assert result[0].model_name == "G4 Doorbell Pro"
    assert result[0].device_type == "camera"
