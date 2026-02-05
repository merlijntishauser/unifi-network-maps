"""Tests for VLAN inventory helpers."""

from __future__ import annotations

from unifi_network_maps.model.vlans import (
    build_network_vlan_map,
    build_vlan_info,
    build_vlan_names,
    normalize_networks,
)

# --- normalize_networks ---


class TestNormalizeNetworks:
    def test_empty_input(self):
        assert normalize_networks([]) == []

    def test_extracts_network_fields(self):
        networks = [{"_id": "net1", "name": "LAN", "vlan": 10, "vlan_enabled": True}]
        result = normalize_networks(networks)
        assert len(result) == 1
        assert result[0]["network_id"] == "net1"
        assert result[0]["name"] == "LAN"
        assert result[0]["vlan_id"] == 10
        assert result[0]["vlan_enabled"] is True

    def test_alternative_field_names(self):
        networks = [{"id": "net2", "network_name": "Guest", "vlanId": 20, "vlanEnabled": True}]
        result = normalize_networks(networks)
        assert result[0]["network_id"] == "net2"
        assert result[0]["name"] == "Guest"
        assert result[0]["vlan_id"] == 20

    def test_vlan_disabled_defaults_to_vlan_1(self):
        networks = [{"name": "Default", "vlan_enabled": False}]
        result = normalize_networks(networks)
        assert result[0]["vlan_id"] == 1

    def test_skips_none_entries(self):
        networks = [{"name": "Valid"}, None, {"name": "Also Valid"}]
        result = normalize_networks(networks)
        assert len(result) == 2

    def test_string_vlan_id(self):
        networks = [{"name": "Test", "vlan": "30", "vlan_enabled": True}]
        result = normalize_networks(networks)
        assert result[0]["vlan_id"] == 30

    def test_invalid_vlan_id_zero(self):
        networks = [{"name": "Test", "vlan": 0, "vlan_enabled": True}]
        result = normalize_networks(networks)
        assert result[0]["vlan_id"] is None

    def test_invalid_vlan_id_negative(self):
        networks = [{"name": "Test", "vlan": -1, "vlan_enabled": True}]
        result = normalize_networks(networks)
        assert result[0]["vlan_id"] is None

    def test_purpose_field(self):
        networks = [{"name": "Corp", "purpose": "corporate", "vlan": 100}]
        result = normalize_networks(networks)
        assert result[0]["purpose"] == "corporate"


# --- build_vlan_info ---


class TestBuildVlanInfo:
    def test_empty_inputs(self):
        result = build_vlan_info([], [])
        assert result == []

    def test_networks_only(self):
        networks = [
            {"name": "LAN", "vlan_enabled": False},
            {"name": "Guest", "vlan": 20},
        ]
        result = build_vlan_info([], networks)
        assert len(result) == 2
        # Results sorted by VLAN ID
        assert result[0]["id"] == 1
        assert result[0]["name"] == "LAN"
        assert result[0]["client_count"] == 0
        assert result[1]["id"] == 20
        assert result[1]["name"] == "Guest"

    def test_clients_only(self):
        clients = [
            {"vlan": 10},
            {"vlan": 10},
            {"vlan": 20},
        ]
        result = build_vlan_info(clients, [])
        assert len(result) == 2
        vlan_map = {r["id"]: r for r in result}
        assert vlan_map[10]["client_count"] == 2
        assert vlan_map[20]["client_count"] == 1
        # No network name when no networks provided
        assert vlan_map[10]["name"] is None

    def test_merges_clients_and_networks(self):
        networks = [{"name": "IoT", "vlan": 30}]
        clients = [{"vlan": 30}, {"vlan": 30}, {"vlan": 40}]
        result = build_vlan_info(clients, networks)
        vlan_map = {r["id"]: r for r in result}
        assert vlan_map[30]["name"] == "IoT"
        assert vlan_map[30]["client_count"] == 2
        assert vlan_map[40]["name"] is None
        assert vlan_map[40]["client_count"] == 1

    def test_clients_with_no_vlan_ignored(self):
        clients = [{"name": "Client A"}, {"vlan": 10}]  # No vlan field
        result = build_vlan_info(clients, [])
        assert len(result) == 1
        assert result[0]["id"] == 10

    def test_results_sorted_by_vlan_id(self):
        networks = [
            {"name": "C", "vlan": 30},
            {"name": "A", "vlan": 10},
            {"name": "B", "vlan": 20},
        ]
        result = build_vlan_info([], networks)
        ids = [r["id"] for r in result]
        assert ids == [10, 20, 30]


# --- build_network_vlan_map ---


class TestBuildNetworkVlanMap:
    def test_empty_networks(self):
        assert build_network_vlan_map([]) == {}

    def test_maps_network_id_to_vlan(self):
        networks = [
            {"_id": "net1", "vlan": 10},
            {"_id": "net2", "vlan": 20},
        ]
        result = build_network_vlan_map(networks)
        assert result == {"net1": 10, "net2": 20}

    def test_skips_missing_network_id(self):
        networks = [
            {"vlan": 10},  # No network ID
            {"_id": "net2", "vlan": 20},
        ]
        result = build_network_vlan_map(networks)
        assert result == {"net2": 20}

    def test_defaults_to_vlan_1_when_missing(self):
        networks = [
            {"_id": "net1"},  # No VLAN -> defaults to 1
            {"_id": "net2", "vlan": 20},
        ]
        result = build_network_vlan_map(networks)
        assert result == {"net1": 1, "net2": 20}


# --- build_vlan_names ---


class TestBuildVlanNames:
    def test_empty_networks(self):
        assert build_vlan_names([]) == {}

    def test_maps_vlan_to_name(self):
        networks = [
            {"name": "LAN", "vlan_enabled": False},
            {"name": "Guest", "vlan": 20},
        ]
        result = build_vlan_names(networks)
        assert result == {1: "LAN", 20: "Guest"}

    def test_first_name_wins_for_duplicate_vlans(self):
        networks = [
            {"name": "First", "vlan": 10},
            {"name": "Second", "vlan": 10},
        ]
        result = build_vlan_names(networks)
        assert result[10] == "First"

    def test_skips_networks_without_name(self):
        networks = [
            {"vlan": 10},  # No name
            {"name": "Named", "vlan": 20},
        ]
        result = build_vlan_names(networks)
        assert 10 not in result
        assert result[20] == "Named"
