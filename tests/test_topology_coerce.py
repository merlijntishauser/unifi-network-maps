"""Tests for topology coercion and device normalization utilities."""

from __future__ import annotations

import pytest

from unifi_network_maps.model.topology_coerce import (
    _aggregation_group,
    _as_float,
    _as_group_id,
    _as_int,
    _coerce_vlan_list,
    _extract_wan_networkconf_id,
    _parse_uplink,
    _port_info_from_entry,
    _resolve_vlan_id,
    coerce_device,
    normalize_devices,
)

# --- _as_int ---


class TestAsInt:
    def test_returns_int_directly(self):
        assert _as_int(42) == 42

    def test_parses_string(self):
        assert _as_int("123") == 123

    def test_invalid_string_returns_none(self):
        assert _as_int("abc") is None

    def test_none_returns_none(self):
        assert _as_int(None) is None

    def test_float_returns_none(self):
        assert _as_int(3.14) is None


# --- _as_float ---


class TestAsFloat:
    def test_returns_float_from_int(self):
        assert _as_float(10) == 10.0

    def test_returns_float_directly(self):
        assert _as_float(3.14) == 3.14

    def test_parses_string(self):
        assert _as_float("2.5") == 2.5

    def test_invalid_string_returns_zero(self):
        assert _as_float("not_a_number") == 0.0

    def test_none_returns_zero(self):
        assert _as_float(None) == 0.0


# --- _as_group_id ---


class TestAsGroupId:
    def test_none_returns_none(self):
        assert _as_group_id(None) is None

    def test_bool_returns_none(self):
        assert _as_group_id(True) is None
        assert _as_group_id(False) is None

    def test_int_returns_string(self):
        assert _as_group_id(5) == "5"

    def test_string_preserved(self):
        assert _as_group_id("lag1") == "lag1"

    def test_empty_string_returns_none(self):
        assert _as_group_id("  ") is None

    def test_other_types_return_none(self):
        assert _as_group_id([1, 2, 3]) is None


# --- _aggregation_group ---


class TestAggregationGroup:
    def test_dict_with_aggregation_group(self):
        assert _aggregation_group({"aggregation_group": "lag1"}) == "lag1"

    def test_dict_with_lag_id(self):
        assert _aggregation_group({"lag_id": 2}) == 2

    def test_dict_with_none_value(self):
        assert _aggregation_group({"aggregation_group": None}) is None

    def test_dict_with_empty_string(self):
        assert _aggregation_group({"aggregation_group": ""}) is None

    def test_dict_with_false_value(self):
        assert _aggregation_group({"aggregation_group": False}) is None

    def test_non_dict_object_with_attribute(self):
        class MockPort:
            def __init__(self):
                self.lag_group = "lag2"

        assert _aggregation_group(MockPort()) == "lag2"

    def test_non_dict_object_no_match(self):
        class MockPort:
            def __init__(self):
                self.other_field = "value"

        assert _aggregation_group(MockPort()) is None


# --- _coerce_vlan_list ---


class TestCoerceVlanList:
    def test_none_returns_empty(self):
        assert _coerce_vlan_list(None) == ()

    def test_special_string_auto(self):
        assert _coerce_vlan_list("auto") == ()

    def test_special_string_block_all(self):
        assert _coerce_vlan_list("block_all") == ()

    def test_special_string_all(self):
        assert _coerce_vlan_list("ALL") == ()

    def test_special_string_none(self):
        assert _coerce_vlan_list("none") == ()

    def test_empty_string(self):
        assert _coerce_vlan_list("") == ()

    def test_comma_separated_string(self):
        assert _coerce_vlan_list("10, 20, 30") == (10, 20, 30)

    def test_single_int(self):
        assert _coerce_vlan_list(100) == (100,)

    def test_list_of_ints(self):
        assert _coerce_vlan_list([30, 10, 20]) == (10, 20, 30)

    def test_list_with_network_ids(self):
        network_map = {"network_a": 10, "network_b": 20}
        result = _coerce_vlan_list(["network_a", 30, "network_b"], network_map)
        assert result == (10, 20, 30)

    def test_list_with_invalid_items(self):
        assert _coerce_vlan_list([10, "invalid", 20]) == (10, 20)

    def test_other_type_returns_empty(self):
        assert _coerce_vlan_list({"not": "a list"}) == ()


# --- _resolve_vlan_id ---


class TestResolveVlanId:
    def test_int_value(self):
        assert _resolve_vlan_id(100) == 100

    def test_string_int_value(self):
        assert _resolve_vlan_id("50") == 50

    def test_network_id_with_map(self):
        network_map = {"my_network": 25}
        assert _resolve_vlan_id("my_network", network_map) == 25

    def test_unknown_network_id_returns_none(self):
        network_map = {"my_network": 25}
        assert _resolve_vlan_id("unknown", network_map) is None

    def test_none_returns_none(self):
        assert _resolve_vlan_id(None) is None


# --- _extract_wan_networkconf_id ---


class TestExtractWanNetworkconfId:
    def test_dict_with_value(self):
        assert _extract_wan_networkconf_id({"wan_networkconf_id": "WAN"}) == "WAN"

    def test_dict_with_empty_value(self):
        assert _extract_wan_networkconf_id({"wan_networkconf_id": "  "}) is None

    def test_dict_without_field(self):
        assert _extract_wan_networkconf_id({}) is None

    def test_non_dict_object_with_attribute(self):
        class MockPort:
            def __init__(self):
                self.wan_networkconf_id = "WAN2"

        assert _extract_wan_networkconf_id(MockPort()) == "WAN2"


# --- _port_info_from_entry ---


class TestPortInfoFromEntry:
    def test_dict_port_entry(self):
        entry = {
            "port_idx": 1,
            "name": "Port 1",
            "ifname": "eth0",
            "speed": 1000,
            "port_poe": True,
            "poe_power": 15.5,
        }
        port = _port_info_from_entry(entry)
        assert port.port_idx == 1
        assert port.name == "Port 1"
        assert port.speed == 1000
        assert port.port_poe is True

    def test_non_dict_port_entry(self):
        class MockPort:
            def __init__(self):
                self.port_idx = 5
                self.portIdx = None  # Alternate field
                self.name = "SFP"
                self.ifname = "sfp0"
                self.speed = 10000
                self.aggregation_group = None
                self.port_poe = False
                self.poe_enable = False
                self.poe_good = False
                self.poe_power = 0.0
                self.native_vlan = 10
                self.tagged_vlans = (20, 30)

        port = _port_info_from_entry(MockPort())
        assert port.port_idx == 5
        assert port.name == "SFP"
        assert port.speed == 10000

    def test_with_network_vlan_map(self):
        entry = {
            "port_idx": 1,
            "native_vlan": "network_lan",
            "tagged_vlans": ["network_guest", "network_iot"],
        }
        network_map = {"network_lan": 1, "network_guest": 20, "network_iot": 30}
        port = _port_info_from_entry(entry, network_map)
        assert port.native_vlan == 1
        assert port.tagged_vlans == (20, 30)


# --- _parse_uplink ---


class TestParseUplink:
    def test_none_returns_none(self):
        assert _parse_uplink(None) is None

    def test_dict_with_fields(self):
        uplink = _parse_uplink(
            {
                "uplink_mac": "aa:bb:cc:dd:ee:ff",
                "uplink_device_name": "Core Switch",
                "uplink_remote_port": 24,
            }
        )
        assert uplink is not None
        assert uplink.mac == "aa:bb:cc:dd:ee:ff"
        assert uplink.name == "Core Switch"
        assert uplink.port == 24

    def test_all_none_returns_none(self):
        assert _parse_uplink({}) is None

    def test_non_dict_with_fields(self):
        class MockUplink:
            def __init__(self):
                self.uplink_mac = "11:22:33:44:55:66"
                self.uplink_device_mac = None
                self.uplink_device_name = "Switch"
                self.uplink_name = None
                self.uplink_remote_port = 10
                self.port_idx = None

        uplink = _parse_uplink(MockUplink())
        assert uplink is not None
        assert uplink.mac == "11:22:33:44:55:66"


# --- coerce_device ---


class TestCoerceDevice:
    def test_minimal_device(self):
        raw = {
            "name": "Test Switch",
            "mac": "aa:bb:cc:dd:ee:ff",
            "lldp_info": [],
        }
        device = coerce_device(raw)
        assert device.name == "Test Switch"
        assert device.mac == "aa:bb:cc:dd:ee:ff"

    def test_missing_name_raises(self):
        raw = {"mac": "aa:bb:cc:dd:ee:ff", "lldp_info": []}
        with pytest.raises(ValueError, match="missing name or mac"):
            coerce_device(raw)

    def test_missing_mac_raises(self):
        raw = {"name": "Switch", "lldp_info": []}
        with pytest.raises(ValueError, match="missing name or mac"):
            coerce_device(raw)

    def test_missing_lldp_with_uplink_uses_fallback(self, caplog):
        raw = {
            "name": "Test AP",
            "mac": "aa:bb:cc:dd:ee:ff",
            "uplink": {
                "uplink_mac": "11:22:33:44:55:66",
                "uplink_device_name": "Switch",
            },
        }
        device = coerce_device(raw)
        assert device.name == "Test AP"
        assert "missing LLDP info" in caplog.text

    def test_missing_lldp_without_uplink_raises(self):
        raw = {"name": "Orphan", "mac": "aa:bb:cc:dd:ee:ff"}
        with pytest.raises(ValueError, match="missing LLDP info"):
            coerce_device(raw)

    def test_model_display_name_priority(self):
        raw = {
            "name": "Switch",
            "mac": "aa:bb:cc:dd:ee:ff",
            "model_in_lts": "USW Pro 24",
            "model_name": "Generic Switch",
            "model": "USW-Pro-24",
            "lldp_info": [],
        }
        device = coerce_device(raw)
        assert device.model_name == "USW Pro 24"


# --- normalize_devices ---


class TestNormalizeDevices:
    def test_normalizes_list(self):
        raw_devices = [
            {"name": "A", "mac": "00:00:00:00:00:01", "lldp_info": []},
            {"name": "B", "mac": "00:00:00:00:00:02", "lldp_info": []},
        ]
        devices = normalize_devices(raw_devices)
        assert len(devices) == 2
        assert devices[0].name == "A"
        assert devices[1].name == "B"
