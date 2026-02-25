"""Tests for device summary helpers."""

from __future__ import annotations

from unifi_topology.model.topology import Device, PortInfo, UplinkInfo

from unifi_network_maps.render.device_summary import poe_summary, port_summary, uplink_summary


def _make_device(
    *,
    name: str = "test-device",
    device_type: str = "switch",
    port_table: list[PortInfo] | None = None,
    uplink: UplinkInfo | None = None,
) -> Device:
    return Device(
        name=name,
        model_name="Test",
        model="TEST",
        mac="aa:bb:cc:dd:ee:ff",
        ip="192.168.1.1",
        type=device_type,
        lldp_info=[],
        port_table=port_table or [],
        poe_ports={},
        uplink=uplink,
        last_uplink=None,
        version="1.0",
    )


def _make_port(
    *,
    idx: int,
    speed: int = 0,
    port_poe: bool = False,
    poe_enable: bool = False,
    poe_good: bool = False,
    poe_power: float | None = None,
) -> PortInfo:
    return PortInfo(
        port_idx=idx,
        name=f"Port {idx}",
        ifname=f"eth{idx}",
        speed=speed,
        aggregation_group=None,
        port_poe=port_poe,
        poe_enable=poe_enable,
        poe_good=poe_good,
        poe_power=poe_power,
    )


# --- port_summary ---


class TestPortSummary:
    def test_no_ports(self):
        device = _make_device()
        assert port_summary(device) == "-"

    def test_all_inactive(self):
        device = _make_device(port_table=[_make_port(idx=1, speed=0), _make_port(idx=2, speed=0)])
        assert port_summary(device) == "2 total, 0 active"

    def test_some_active(self):
        device = _make_device(
            port_table=[
                _make_port(idx=1, speed=1000),
                _make_port(idx=2, speed=0),
                _make_port(idx=3, speed=100),
            ]
        )
        assert port_summary(device) == "3 total, 2 active"

    def test_all_active(self):
        device = _make_device(
            port_table=[_make_port(idx=1, speed=1000), _make_port(idx=2, speed=1000)]
        )
        assert port_summary(device) == "2 total, 2 active"

    def test_skips_ports_without_idx(self):
        port_no_idx = PortInfo(
            port_idx=None,
            name="SFP",
            ifname="sfp0",
            speed=10000,
            aggregation_group=None,
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=None,
        )
        device = _make_device(port_table=[_make_port(idx=1, speed=1000), port_no_idx])
        assert port_summary(device) == "1 total, 1 active"


# --- poe_summary ---


class TestPoeSummary:
    def test_no_ports(self):
        device = _make_device()
        assert poe_summary(device) == "-"

    def test_no_poe_capable(self):
        device = _make_device(port_table=[_make_port(idx=1), _make_port(idx=2)])
        assert "0 capable" in poe_summary(device)

    def test_poe_capable_none_active(self):
        device = _make_device(
            port_table=[
                _make_port(idx=1, port_poe=True),
                _make_port(idx=2, port_poe=True),
            ]
        )
        result = poe_summary(device)
        assert "2 capable" in result
        assert "0 active" in result

    def test_poe_active_with_power(self):
        device = _make_device(
            port_table=[
                _make_port(idx=1, port_poe=True, poe_good=True, poe_power=15.5),
                _make_port(idx=2, port_poe=True, poe_power=10.0),
            ]
        )
        result = poe_summary(device)
        assert "2 capable" in result
        assert "2 active" in result
        assert "25.50W" in result

    def test_poe_enable_counts_as_capable(self):
        device = _make_device(port_table=[_make_port(idx=1, poe_enable=True)])
        assert "1 capable" in poe_summary(device)


# --- uplink_summary ---


class TestUplinkSummary:
    def test_no_uplink_switch(self):
        device = _make_device(device_type="switch")
        assert uplink_summary(device) == "-"

    def test_no_uplink_gateway(self):
        device = _make_device(device_type="gateway")
        assert uplink_summary(device) == "Internet"

    def test_with_uplink_name_and_port(self):
        uplink = UplinkInfo(mac="11:22:33:44:55:66", name="Core Switch", port=24)
        device = _make_device(uplink=uplink)
        assert uplink_summary(device) == "Core Switch (Port 24)"

    def test_with_uplink_name_only(self):
        uplink = UplinkInfo(mac="11:22:33:44:55:66", name="Core Switch", port=None)
        device = _make_device(uplink=uplink)
        assert uplink_summary(device) == "Core Switch"

    def test_with_uplink_mac_only(self):
        uplink = UplinkInfo(mac="11:22:33:44:55:66", name=None, port=None)
        device = _make_device(uplink=uplink)
        assert uplink_summary(device) == "11:22:33:44:55:66"

    def test_gateway_wan_uplink_becomes_internet(self):
        uplink = UplinkInfo(mac="11:22:33:44:55:66", name="WAN", port=1)
        device = _make_device(device_type="gateway", uplink=uplink)
        assert "Internet" in uplink_summary(device)

    def test_gateway_eth_uplink_becomes_internet(self):
        uplink = UplinkInfo(mac="11:22:33:44:55:66", name="eth0", port=1)
        device = _make_device(device_type="gateway", uplink=uplink)
        assert "Internet" in uplink_summary(device)

    def test_gateway_unknown_uplink_becomes_internet(self):
        uplink = UplinkInfo(mac="11:22:33:44:55:66", name="Unknown", port=1)
        device = _make_device(device_type="gateway", uplink=uplink)
        assert "Internet" in uplink_summary(device)
