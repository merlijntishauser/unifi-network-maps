"""Tests for topology diff API."""

from __future__ import annotations

import json

import pytest

from unifi_network_maps.model.diff import (
    TopologyChangeEvent,
    TopologyDiff,
    compare_topologies,
)
from unifi_network_maps.model.snapshot import (
    device_from_dict,
    device_to_dict,
    edge_from_dict,
    edge_to_dict,
)
from unifi_network_maps.model.topology import Device, Edge, Topology

# --- Fixtures ---


@pytest.fixture
def sample_device() -> Device:
    """Create a sample device for testing."""
    return Device(
        name="switch-1",
        model_name="UniFi Switch Pro 24",
        model="USW-Pro-24",
        mac="aa:bb:cc:dd:ee:ff",
        ip="192.168.1.10",
        type="switch",
        lldp_info=[],
        port_table=[],
        poe_ports={},
        uplink=None,
        last_uplink=None,
        version="6.5.0",
    )


@pytest.fixture
def sample_device_2() -> Device:
    """Create a second sample device."""
    return Device(
        name="ap-1",
        model_name="UniFi AP Pro",
        model="UAP-AC-Pro",
        mac="11:22:33:44:55:66",
        ip="192.168.1.20",
        type="ap",
        lldp_info=[],
        port_table=[],
        poe_ports={},
        uplink=None,
        last_uplink=None,
        version="6.5.0",
    )


@pytest.fixture
def sample_client() -> dict[str, object]:
    """Create a sample client for testing."""
    return {
        "mac": "cc:dd:ee:ff:00:11",
        "name": "laptop-1",
        "ip": "192.168.1.100",
        "vlan": 10,
        "is_wired": True,
        "sw_mac": "aa:bb:cc:dd:ee:ff",
        "sw_port": 5,
    }


@pytest.fixture
def sample_edge() -> Edge:
    """Create a sample edge for testing."""
    return Edge(
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


# --- TopologyChangeEvent tests ---


class TestTopologyChangeEvent:
    def test_to_dict(self):
        event = TopologyChangeEvent(
            event_type="node_added",
            entity_type="device",
            identifier="aa:bb:cc:dd:ee:ff",
            name="switch-1",
            description="Device 'switch-1' appeared on network",
            details={"ip": "192.168.1.10"},
            timestamp="2026-02-05T10:00:00Z",
        )
        result = event.to_dict()
        assert result["event_type"] == "node_added"
        assert result["entity_type"] == "device"
        assert result["identifier"] == "aa:bb:cc:dd:ee:ff"
        assert result["name"] == "switch-1"
        assert result["description"] == "Device 'switch-1' appeared on network"
        assert result["details"]["ip"] == "192.168.1.10"
        assert result["timestamp"] == "2026-02-05T10:00:00Z"

    def test_to_dict_is_json_serializable(self):
        event = TopologyChangeEvent(
            event_type="node_changed",
            entity_type="client",
            identifier="cc:dd:ee:ff:00:11",
            name="laptop",
            description="Client changed",
            details={"changes": {"vlan": {"old": 10, "new": 20}}},
        )
        json_str = json.dumps(event.to_dict())
        assert "node_changed" in json_str


# --- TopologyDiff tests ---


class TestTopologyDiff:
    def test_empty_diff(self):
        diff = TopologyDiff()
        assert diff.events == []
        assert diff.summary == ""

    def test_to_dict(self):
        event = TopologyChangeEvent(
            event_type="node_added",
            entity_type="device",
            identifier="aa:bb:cc:dd:ee:ff",
            name="switch-1",
            description="Device added",
        )
        diff = TopologyDiff(
            events=[event],
            old_timestamp="2026-02-05T09:00:00Z",
            new_timestamp="2026-02-05T10:00:00Z",
            summary="1 device added",
        )
        result = diff.to_dict()
        assert len(result["events"]) == 1
        assert result["old_timestamp"] == "2026-02-05T09:00:00Z"
        assert result["new_timestamp"] == "2026-02-05T10:00:00Z"
        assert result["summary"] == "1 device added"

    def test_to_json(self):
        diff = TopologyDiff(
            events=[
                TopologyChangeEvent(
                    event_type="node_added",
                    entity_type="device",
                    identifier="aa:bb:cc:dd:ee:ff",
                    name="switch-1",
                    description="Device added",
                )
            ],
            summary="1 device added",
        )
        json_str = diff.to_json()
        parsed = json.loads(json_str)
        assert len(parsed["events"]) == 1
        assert parsed["summary"] == "1 device added"

    def test_filter_by_event_type(self):
        events = [
            TopologyChangeEvent(
                event_type="node_added",
                entity_type="device",
                identifier="a",
                name="a",
                description="",
            ),
            TopologyChangeEvent(
                event_type="node_removed",
                entity_type="device",
                identifier="b",
                name="b",
                description="",
            ),
            TopologyChangeEvent(
                event_type="edge_added",
                entity_type="device",
                identifier="c",
                name=None,
                description="",
            ),
        ]
        diff = TopologyDiff(events=events, summary="test")
        filtered = diff.filter(event_types={"node_added", "node_removed"})
        assert len(filtered.events) == 2
        assert all(e.event_type in {"node_added", "node_removed"} for e in filtered.events)

    def test_filter_by_entity_type(self):
        events = [
            TopologyChangeEvent(
                event_type="node_added",
                entity_type="device",
                identifier="a",
                name="a",
                description="",
            ),
            TopologyChangeEvent(
                event_type="node_added",
                entity_type="client",
                identifier="b",
                name="b",
                description="",
            ),
        ]
        diff = TopologyDiff(events=events, summary="test")
        filtered = diff.filter(entity_types={"client"})
        assert len(filtered.events) == 1
        assert filtered.events[0].entity_type == "client"


# --- compare_topologies tests ---


class TestCompareTopologies:
    def test_empty_topologies(self):
        diff = compare_topologies([], [])
        assert len(diff.events) == 0
        assert diff.summary == "No changes"

    def test_identical_topologies(self, sample_device: Device):
        diff = compare_topologies([sample_device], [sample_device])
        assert len(diff.events) == 0

    def test_device_added(self, sample_device: Device):
        diff = compare_topologies([], [sample_device])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "node_added"
        assert event.entity_type == "device"
        assert event.name == "switch-1"
        assert "appeared" in event.description

    def test_device_removed(self, sample_device: Device):
        diff = compare_topologies([sample_device], [])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "node_removed"
        assert event.entity_type == "device"
        assert "disappeared" in event.description

    def test_device_changed_ip(self, sample_device: Device):
        old_device = sample_device
        new_device = Device(
            name=sample_device.name,
            model_name=sample_device.model_name,
            model=sample_device.model,
            mac=sample_device.mac,
            ip="192.168.1.11",  # Changed IP
            type=sample_device.type,
            lldp_info=sample_device.lldp_info,
            port_table=sample_device.port_table,
            poe_ports=sample_device.poe_ports,
            uplink=sample_device.uplink,
            last_uplink=sample_device.last_uplink,
            version=sample_device.version,
        )
        diff = compare_topologies([old_device], [new_device])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "node_changed"
        assert "ip" in event.details["changes"]
        assert event.details["changes"]["ip"]["old"] == "192.168.1.10"
        assert event.details["changes"]["ip"]["new"] == "192.168.1.11"

    def test_device_renamed(self, sample_device: Device):
        new_device = Device(
            name="switch-main",  # Renamed
            model_name=sample_device.model_name,
            model=sample_device.model,
            mac=sample_device.mac,  # Same MAC = same device
            ip=sample_device.ip,
            type=sample_device.type,
            lldp_info=sample_device.lldp_info,
            port_table=sample_device.port_table,
            poe_ports=sample_device.poe_ports,
            uplink=sample_device.uplink,
            last_uplink=sample_device.last_uplink,
            version=sample_device.version,
        )
        diff = compare_topologies([sample_device], [new_device])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "node_changed"
        assert "renamed" in event.description.lower() or "name" in event.details["changes"]

    def test_client_added(self, sample_client: dict[str, object]):
        diff = compare_topologies([], [], old_clients=[], new_clients=[sample_client])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "node_added"
        assert event.entity_type == "client"
        assert "connected" in event.description

    def test_client_removed(self, sample_client: dict[str, object]):
        diff = compare_topologies([], [], old_clients=[sample_client], new_clients=[])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "node_removed"
        assert event.entity_type == "client"
        assert "disconnected" in event.description

    def test_client_vlan_changed(self, sample_client: dict[str, object]):
        new_client = dict(sample_client)
        new_client["vlan"] = 20  # Changed VLAN
        diff = compare_topologies([], [], old_clients=[sample_client], new_clients=[new_client])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "node_changed"
        assert event.entity_type == "client"
        assert "VLAN" in event.description
        assert event.details["changes"]["vlan"]["old"] == 10
        assert event.details["changes"]["vlan"]["new"] == 20

    def test_edge_added(self, sample_edge: Edge):
        diff = compare_topologies([], [], old_edges=[], new_edges=[sample_edge])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "edge_added"
        assert "added" in event.description

    def test_edge_removed(self, sample_edge: Edge):
        diff = compare_topologies([], [], old_edges=[sample_edge], new_edges=[])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "edge_removed"
        assert "removed" in event.description

    def test_edge_changed_speed(self, sample_edge: Edge):
        new_edge = Edge(
            left=sample_edge.left,
            right=sample_edge.right,
            label=sample_edge.label,
            poe=sample_edge.poe,
            wireless=sample_edge.wireless,
            speed=10000,  # Changed speed
            channel=sample_edge.channel,
            vlans=sample_edge.vlans,
            active_vlans=sample_edge.active_vlans,
            is_trunk=sample_edge.is_trunk,
        )
        diff = compare_topologies([], [], old_edges=[sample_edge], new_edges=[new_edge])
        assert len(diff.events) == 1
        event = diff.events[0]
        assert event.event_type == "edge_changed"
        assert "speed" in event.details["changes"]

    def test_multiple_changes(
        self,
        sample_device: Device,
        sample_device_2: Device,
        sample_client: dict[str, object],
    ):
        diff = compare_topologies(
            [sample_device],
            [sample_device, sample_device_2],
            old_clients=[sample_client],
            new_clients=[],
        )
        # Should have: 1 device added (sample_device_2), 1 client removed
        assert len(diff.events) == 2
        event_types = {e.event_type for e in diff.events}
        assert "node_added" in event_types
        assert "node_removed" in event_types

    def test_summary_generation(
        self,
        sample_device: Device,
        sample_device_2: Device,
    ):
        diff = compare_topologies([], [sample_device, sample_device_2])
        assert "2 devices added" in diff.summary

    def test_timestamps_passed_through(self, sample_device: Device):
        diff = compare_topologies(
            [sample_device],
            [sample_device],
            old_timestamp="2026-02-05T09:00:00Z",
            new_timestamp="2026-02-05T10:00:00Z",
        )
        assert diff.old_timestamp == "2026-02-05T09:00:00Z"
        assert diff.new_timestamp == "2026-02-05T10:00:00Z"


# --- Serialization round-trip tests ---


class TestSerializationRoundTrip:
    def test_device_round_trip(self, sample_device: Device):
        data = device_to_dict(sample_device)
        restored = device_from_dict(data)
        assert restored.name == sample_device.name
        assert restored.mac == sample_device.mac
        assert restored.ip == sample_device.ip
        assert restored.model == sample_device.model
        assert restored.type == sample_device.type
        assert restored.version == sample_device.version

    def test_edge_round_trip(self, sample_edge: Edge):
        data = edge_to_dict(sample_edge)
        restored = edge_from_dict(data)
        assert restored.left == sample_edge.left
        assert restored.right == sample_edge.right
        assert restored.poe == sample_edge.poe
        assert restored.speed == sample_edge.speed
        assert restored.vlans == sample_edge.vlans
        assert restored.is_trunk == sample_edge.is_trunk

    def test_topology_round_trip(
        self,
        sample_device: Device,
        sample_client: dict[str, object],
        sample_edge: Edge,
    ):
        topology = Topology(
            devices=[sample_device],
            clients=[sample_client],
            edges=[sample_edge],
            timestamp="2026-02-05T10:00:00Z",
        )
        data = topology.to_dict()
        restored = Topology.from_dict(data)
        assert len(restored.devices) == 1
        assert restored.devices[0].name == sample_device.name
        assert len(restored.clients) == 1
        assert restored.clients[0]["mac"] == sample_client["mac"]
        assert len(restored.edges) == 1
        assert restored.edges[0].left == sample_edge.left
        assert restored.timestamp == "2026-02-05T10:00:00Z"

    def test_topology_json_round_trip(
        self,
        sample_device: Device,
        sample_edge: Edge,
    ):
        topology = Topology(
            devices=[sample_device],
            edges=[sample_edge],
            timestamp="2026-02-05T10:00:00Z",
        )
        json_str = json.dumps(topology.to_dict())
        data = json.loads(json_str)
        restored = Topology.from_dict(data)
        assert restored.devices[0].mac == sample_device.mac


# --- Topology.diff() method tests ---


class TestTopologyDiffMethod:
    def test_diff_method(self, sample_device: Device, sample_device_2: Device):
        old = Topology(devices=[sample_device])
        new = Topology(devices=[sample_device, sample_device_2])
        diff = old.diff(new)
        assert len(diff.events) == 1
        assert diff.events[0].event_type == "node_added"
        assert diff.events[0].name == "ap-1"

    def test_diff_method_with_clients(
        self,
        sample_device: Device,
        sample_client: dict[str, object],
    ):
        old = Topology(devices=[sample_device], clients=[sample_client])
        new = Topology(devices=[sample_device], clients=[])
        diff = old.diff(new)
        assert len(diff.events) == 1
        assert diff.events[0].event_type == "node_removed"
        assert diff.events[0].entity_type == "client"

    def test_diff_method_timestamps(self, sample_device: Device):
        old = Topology(devices=[sample_device], timestamp="2026-02-05T09:00:00Z")
        new = Topology(devices=[sample_device], timestamp="2026-02-05T10:00:00Z")
        diff = old.diff(new)
        assert diff.old_timestamp == "2026-02-05T09:00:00Z"
        assert diff.new_timestamp == "2026-02-05T10:00:00Z"


# --- Description generation tests ---


class TestDescriptionGeneration:
    def test_device_added_description(self, sample_device: Device):
        diff = compare_topologies([], [sample_device])
        assert "switch-1" in diff.events[0].description
        assert "appeared" in diff.events[0].description

    def test_device_removed_description(self, sample_device: Device):
        diff = compare_topologies([sample_device], [])
        assert "switch-1" in diff.events[0].description
        assert "disappeared" in diff.events[0].description

    def test_client_wifi_description(self):
        wifi_client = {
            "mac": "aa:bb:cc:dd:ee:ff",
            "name": "phone",
            "is_wired": False,
        }
        diff = compare_topologies([], [], old_clients=[], new_clients=[wifi_client])
        assert "WiFi" in diff.events[0].description

    def test_client_wired_description(self):
        wired_client = {
            "mac": "aa:bb:cc:dd:ee:ff",
            "name": "desktop",
            "is_wired": True,
        }
        diff = compare_topologies([], [], old_clients=[], new_clients=[wired_client])
        assert "wired" in diff.events[0].description
