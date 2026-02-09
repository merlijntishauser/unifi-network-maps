"""Tests for device inventory table rendering."""

from unifi_network_maps.model.inventory import DeviceInfo
from unifi_network_maps.render.inventory import render_device_inventory_table


def _info(
    name: str = "SW1",
    device_type: str = "switch",
    ip: str = "192.168.1.10",
    hostname: str | None = None,
) -> DeviceInfo:
    return DeviceInfo(
        name=name,
        device_type=device_type,
        model_name="US-24",
        ip=ip,
        hostname=hostname,
        mac="aa:bb:cc:dd:ee:ff",
        firmware="7.0.0",
    )


def test_render_table_with_hostname():
    table = render_device_inventory_table([_info(hostname="sw1.local")], include_hostname=True)
    assert "Hostname" in table
    assert "sw1.local" in table
    assert "| SW1 |" in table


def test_render_table_without_hostname():
    table = render_device_inventory_table([_info()], include_hostname=False)
    assert "Hostname" not in table
    assert "| SW1 |" in table


def test_render_table_empty():
    table = render_device_inventory_table([], include_hostname=True)
    assert table == ""


def test_render_table_hostname_none_shows_empty():
    table = render_device_inventory_table([_info(hostname=None)], include_hostname=True)
    assert "|  |" in table or "| |" in table


def test_render_table_multiple_devices():
    devices = [
        _info(name="GW", ip="192.168.1.1"),
        _info(name="SW1", ip="192.168.1.10"),
    ]
    table = render_device_inventory_table(devices, include_hostname=False)
    lines = table.strip().split("\n")
    assert len(lines) == 4  # header + separator + 2 rows
