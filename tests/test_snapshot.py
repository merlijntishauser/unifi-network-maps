"""Tests for topology snapshot serialization."""

from __future__ import annotations

from unifi_network_maps.model.lldp import LLDPEntry
from unifi_network_maps.model.snapshot import (
    client_from_dict,
    client_to_dict,
    device_from_dict,
    device_to_dict,
    edge_from_dict,
    edge_to_dict,
    lldp_entry_from_dict,
    lldp_entry_to_dict,
    port_info_from_dict,
    port_info_to_dict,
    uplink_info_from_dict,
    uplink_info_to_dict,
    wan_info_from_dict,
    wan_info_to_dict,
    wan_interface_from_dict,
    wan_interface_to_dict,
)
from unifi_network_maps.model.topology import (
    Device,
    Edge,
    PortInfo,
    UplinkInfo,
    WanInfo,
    WanInterface,
)

# --- PortInfo ---


class TestPortInfoSerialization:
    def test_round_trip(self):
        port = PortInfo(
            port_idx=1,
            name="Port 1",
            ifname="eth0",
            speed=1000,
            aggregation_group="lag1",
            port_poe=True,
            poe_enable=True,
            poe_good=True,
            poe_power=15.5,
            native_vlan=10,
            tagged_vlans=(20, 30),
            wan_networkconf_id="WAN",
        )
        data = port_info_to_dict(port)
        restored = port_info_from_dict(data)
        assert restored.port_idx == 1
        assert restored.name == "Port 1"
        assert restored.speed == 1000
        assert restored.poe_power == 15.5
        assert restored.tagged_vlans == (20, 30)

    def test_defaults_for_missing_fields(self):
        data = {"port_idx": 5}
        port = port_info_from_dict(data)
        assert port.port_idx == 5
        assert port.name is None
        assert port.port_poe is False
        assert port.tagged_vlans == ()


# --- UplinkInfo ---


class TestUplinkInfoSerialization:
    def test_round_trip(self):
        uplink = UplinkInfo(mac="aa:bb:cc:dd:ee:ff", name="Switch", port=24)
        data = uplink_info_to_dict(uplink)
        restored = uplink_info_from_dict(data)
        assert restored.mac == "aa:bb:cc:dd:ee:ff"
        assert restored.name == "Switch"
        assert restored.port == 24

    def test_handles_none_values(self):
        uplink = UplinkInfo(mac=None, name=None, port=None)
        data = uplink_info_to_dict(uplink)
        restored = uplink_info_from_dict(data)
        assert restored.mac is None


# --- LLDPEntry ---


class TestLLDPEntrySerialization:
    def test_round_trip(self):
        entry = LLDPEntry(
            chassis_id="aa:bb:cc:dd:ee:ff",
            port_id="eth0",
            port_desc="Uplink to Core",
            local_port_name="Port 24",
            local_port_idx=24,
        )
        data = lldp_entry_to_dict(entry)
        restored = lldp_entry_from_dict(data)
        assert restored.chassis_id == "aa:bb:cc:dd:ee:ff"
        assert restored.port_id == "eth0"
        assert restored.port_desc == "Uplink to Core"
        assert restored.local_port_idx == 24

    def test_defaults_for_missing_fields(self):
        data = {"chassis_id": "aa:bb:cc:dd:ee:ff"}
        entry = lldp_entry_from_dict(data)
        assert entry.chassis_id == "aa:bb:cc:dd:ee:ff"
        assert entry.port_id == ""
        assert entry.port_desc is None


# --- WanInterface ---


class TestWanInterfaceSerialization:
    def test_round_trip(self):
        wan = WanInterface(
            port_idx=1,
            link_speed=10000,
            ip_address="203.0.113.1",
            enabled=True,
            label="Fiber",
            isp_speed="1000/1000",
        )
        data = wan_interface_to_dict(wan)
        restored = wan_interface_from_dict(data)
        assert restored.port_idx == 1
        assert restored.link_speed == 10000
        assert restored.ip_address == "203.0.113.1"
        assert restored.enabled is True
        assert restored.label == "Fiber"
        assert restored.isp_speed == "1000/1000"


# --- WanInfo ---


class TestWanInfoSerialization:
    def test_round_trip_single_wan(self):
        wan1 = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        info = WanInfo(wan1=wan1, wan2=None)
        data = wan_info_to_dict(info)
        restored = wan_info_from_dict(data)
        assert restored.wan1 is not None
        assert restored.wan1.port_idx == 1
        assert restored.wan2 is None

    def test_round_trip_dual_wan(self):
        wan1 = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan2 = WanInterface(port_idx=9, link_speed=100, ip_address=None, enabled=False)
        info = WanInfo(wan1=wan1, wan2=wan2)
        data = wan_info_to_dict(info)
        restored = wan_info_from_dict(data)
        assert restored.wan1 is not None
        assert restored.wan2 is not None
        assert restored.wan2.port_idx == 9


# --- Device ---


class TestDeviceSerialization:
    def test_round_trip(self):
        device = Device(
            name="switch-1",
            model_name="UniFi Switch Pro 24",
            model="USW-Pro-24",
            mac="aa:bb:cc:dd:ee:ff",
            ip="192.168.1.10",
            type="switch",
            lldp_info=[LLDPEntry(chassis_id="11:22:33:44:55:66", port_id="eth0")],
            port_table=[
                PortInfo(
                    port_idx=1,
                    name="Port 1",
                    ifname="eth0",
                    speed=1000,
                    aggregation_group=None,
                    port_poe=True,
                    poe_enable=True,
                    poe_good=True,
                    poe_power=10.0,
                )
            ],
            poe_ports={1: True, 2: False},
            uplink=UplinkInfo(mac="00:11:22:33:44:55", name="Gateway", port=1),
            last_uplink=None,
            version="6.5.0",
        )
        data = device_to_dict(device)
        restored = device_from_dict(data)
        assert restored.name == "switch-1"
        assert restored.mac == "aa:bb:cc:dd:ee:ff"
        assert len(restored.lldp_info) == 1
        assert len(restored.port_table) == 1
        assert restored.poe_ports[1] is True
        assert restored.uplink is not None
        assert restored.uplink.name == "Gateway"

    def test_defaults_for_missing_fields(self):
        data = {"name": "test", "mac": "aa:bb:cc:dd:ee:ff"}
        device = device_from_dict(data)
        assert device.name == "test"
        assert device.lldp_info == []
        assert device.port_table == []
        assert device.poe_ports == {}


# --- Edge ---


class TestEdgeSerialization:
    def test_round_trip(self):
        edge = Edge(
            left="switch-1",
            right="ap-1",
            label="Port 24",
            poe=True,
            wireless=False,
            speed=1000,
            channel=None,
            vlans=(1, 10, 20),
            active_vlans=(1, 10),
            is_trunk=True,
        )
        data = edge_to_dict(edge)
        restored = edge_from_dict(data)
        assert restored.left == "switch-1"
        assert restored.right == "ap-1"
        assert restored.poe is True
        assert restored.vlans == (1, 10, 20)
        assert restored.is_trunk is True

    def test_defaults_for_missing_fields(self):
        data = {"left": "a", "right": "b"}
        edge = edge_from_dict(data)
        assert edge.left == "a"
        assert edge.poe is False
        assert edge.vlans == ()


# --- Client ---


class TestClientSerialization:
    def test_filters_relevant_keys(self):
        client = {
            "mac": "aa:bb:cc:dd:ee:ff",
            "name": "laptop",
            "ip": "192.168.1.100",
            "vlan": 10,
            "is_wired": True,
            "sw_mac": "11:22:33:44:55:66",
            "sw_port": 5,
            "irrelevant_field": "should_be_excluded",
            "another_field": 123,
        }
        data = client_to_dict(client)
        assert "mac" in data
        assert "name" in data
        assert "irrelevant_field" not in data
        assert "another_field" not in data

    def test_from_dict_preserves_all(self):
        data = {"mac": "aa:bb:cc:dd:ee:ff", "name": "test", "custom": "value"}
        client = client_from_dict(data)
        assert client["mac"] == "aa:bb:cc:dd:ee:ff"
        assert client["custom"] == "value"
