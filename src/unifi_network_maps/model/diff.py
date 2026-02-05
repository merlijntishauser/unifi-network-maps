"""Topology comparison and change detection.

Provides functions to compare two topology snapshots and generate structured
change events for integration with monitoring systems like Home Assistant.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .helpers import normalize_mac
from .snapshot import device_to_dict, edge_to_dict
from .topology import Device, Edge


@dataclass
class TopologyChangeEvent:
    """A single change detected between two topology snapshots."""

    event_type: str
    """One of: node_added, node_removed, node_changed, edge_added, edge_removed, edge_changed"""

    entity_type: str
    """'device' or 'client'"""

    identifier: str
    """MAC address - stable identifier across renames"""

    name: str | None
    """Human-readable name (from newer topology if changed)"""

    description: str
    """Human-readable message for notifications"""

    details: dict[str, Any] = field(default_factory=dict)
    """Event-specific payload"""

    timestamp: str | None = None
    """ISO timestamp if available"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "identifier": self.identifier,
            "name": self.name,
            "description": self.description,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class TopologyDiff:
    """Result of comparing two topology snapshots."""

    events: list[TopologyChangeEvent] = field(default_factory=list)
    """All detected changes"""

    old_timestamp: str | None = None
    """Timestamp from old topology metadata"""

    new_timestamp: str | None = None
    """Timestamp from new topology metadata"""

    summary: str = ""
    """Human-readable summary like '3 devices added, 1 removed'"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "events": [e.to_dict() for e in self.events],
            "old_timestamp": self.old_timestamp,
            "new_timestamp": self.new_timestamp,
            "summary": self.summary,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def filter(
        self,
        event_types: set[str] | None = None,
        entity_types: set[str] | None = None,
    ) -> TopologyDiff:
        """Return filtered diff with only matching events."""
        filtered = [
            e
            for e in self.events
            if (event_types is None or e.event_type in event_types)
            and (entity_types is None or e.entity_type in entity_types)
        ]
        return TopologyDiff(
            events=filtered,
            old_timestamp=self.old_timestamp,
            new_timestamp=self.new_timestamp,
            summary=_build_summary(filtered),
        )


def _pluralize(count: int, singular: str) -> str:
    """Return 'N item' or 'N items' based on count."""
    return f"{count} {singular}{'s' if count != 1 else ''}"


def _add_count_part(parts: list[str], count: int, noun: str, verb: str) -> None:
    """Add a count part to the summary list if count > 0."""
    if count:
        parts.append(f"{_pluralize(count, noun)} {verb}")


def _build_summary(events: list[TopologyChangeEvent]) -> str:
    """Build a human-readable summary of changes."""
    counts: dict[str, int] = {}
    for event in events:
        key = f"{event.entity_type}_{event.event_type}"
        counts[key] = counts.get(key, 0) + 1

    parts: list[str] = []

    # Devices
    _add_count_part(parts, counts.get("device_node_added", 0), "device", "added")
    _add_count_part(parts, counts.get("device_node_removed", 0), "device", "removed")
    _add_count_part(parts, counts.get("device_node_changed", 0), "device", "changed")

    # Clients
    _add_count_part(parts, counts.get("client_node_added", 0), "client", "added")
    _add_count_part(parts, counts.get("client_node_removed", 0), "client", "removed")
    _add_count_part(parts, counts.get("client_node_changed", 0), "client", "changed")

    # Edges (combine device and client edges)
    edge_added = counts.get("device_edge_added", 0) + counts.get("client_edge_added", 0)
    edge_removed = counts.get("device_edge_removed", 0) + counts.get("client_edge_removed", 0)
    edge_changed = counts.get("device_edge_changed", 0) + counts.get("client_edge_changed", 0)
    _add_count_part(parts, edge_added, "connection", "added")
    _add_count_part(parts, edge_removed, "connection", "removed")
    _add_count_part(parts, edge_changed, "connection", "changed")

    return ", ".join(parts) if parts else "No changes"


# --- Node comparison ---


def _device_properties(device: Device) -> dict[str, Any]:
    """Extract comparable properties from a device."""
    return {
        "name": device.name,
        "model": device.model,
        "model_name": device.model_name,
        "ip": device.ip,
        "type": device.type,
        "version": device.version,
        "uplink_mac": device.uplink.mac if device.uplink else None,
        "uplink_port": device.uplink.port if device.uplink else None,
    }


def _client_properties(client: dict[str, Any]) -> dict[str, Any]:
    """Extract comparable properties from a client."""
    return {
        "name": client.get("name") or client.get("hostname"),
        "ip": client.get("ip"),
        "vlan": client.get("vlan") or client.get("vlan_id"),
        "is_wired": client.get("is_wired"),
        "uplink_mac": (client.get("ap_mac") or client.get("sw_mac") or client.get("uplink_mac")),
        "uplink_port": client.get("sw_port") or client.get("uplink_remote_port"),
        "channel": client.get("channel"),
        "signal": client.get("signal"),
        "satisfaction": client.get("satisfaction"),
    }


def _compare_properties(
    old_props: dict[str, Any],
    new_props: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Compare two property dicts and return changes."""
    changes: dict[str, dict[str, Any]] = {}
    all_keys = set(old_props.keys()) | set(new_props.keys())
    for key in all_keys:
        old_val = old_props.get(key)
        new_val = new_props.get(key)
        if old_val != new_val:
            changes[key] = {"old": old_val, "new": new_val}
    return changes


def _describe_device_added(device: Device) -> str:
    """Generate description for device added event."""
    return f"Device '{device.name}' appeared on network"


def _describe_device_removed(device: Device) -> str:
    """Generate description for device removed event."""
    return f"Device '{device.name}' disappeared from network"


def _describe_device_changed(device: Device, changes: dict[str, dict[str, Any]]) -> str:
    """Generate description for device changed event."""
    if len(changes) == 1:
        key = list(changes.keys())[0]
        old_val = changes[key]["old"]
        new_val = changes[key]["new"]
        if key == "ip":
            return f"Device '{device.name}' IP changed from {old_val} to {new_val}"
        if key == "name":
            return f"Device renamed from '{old_val}' to '{new_val}'"
        if key == "uplink_mac":
            return f"Device '{device.name}' uplink changed"
        if key == "uplink_port":
            return f"Device '{device.name}' moved to port {new_val}"
        return f"Device '{device.name}' {key} changed"
    return f"Device '{device.name}' changed ({len(changes)} properties)"


def _describe_client_added(client: dict[str, Any]) -> str:
    """Generate description for client added event."""
    name = client.get("name") or client.get("hostname") or client.get("mac", "unknown")
    is_wired = client.get("is_wired", True)
    conn_type = "wired" if is_wired else "WiFi"
    return f"Client '{name}' connected via {conn_type}"


def _describe_client_removed(client: dict[str, Any]) -> str:
    """Generate description for client removed event."""
    name = client.get("name") or client.get("hostname") or client.get("mac", "unknown")
    return f"Client '{name}' disconnected"


def _describe_client_changed(client: dict[str, Any], changes: dict[str, dict[str, Any]]) -> str:
    """Generate description for client changed event."""
    name = client.get("name") or client.get("hostname") or client.get("mac", "unknown")
    if len(changes) == 1:
        key = list(changes.keys())[0]
        old_val = changes[key]["old"]
        new_val = changes[key]["new"]
        if key == "vlan":
            return f"Client '{name}' changed VLAN from {old_val} to {new_val}"
        if key == "ip":
            return f"Client '{name}' IP changed from {old_val} to {new_val}"
        if key == "uplink_mac":
            return f"Client '{name}' moved to different device"
        if key == "uplink_port":
            return f"Client '{name}' moved to port {new_val}"
        return f"Client '{name}' {key} changed"
    return f"Client '{name}' changed ({len(changes)} properties)"


# --- Edge comparison ---


def _edge_key(edge: Edge) -> frozenset[str]:
    """Create a stable key for an edge (order-independent)."""
    return frozenset({edge.left, edge.right})


def _edge_properties(edge: Edge) -> dict[str, Any]:
    """Extract comparable properties from an edge."""
    return {
        "label": edge.label,
        "poe": edge.poe,
        "wireless": edge.wireless,
        "speed": edge.speed,
        "channel": edge.channel,
        "vlans": edge.vlans,
        "is_trunk": edge.is_trunk,
    }


def _describe_edge_added(edge: Edge) -> str:
    """Generate description for edge added event."""
    conn_type = "wireless" if edge.wireless else "wired"
    return f"Connection added: {edge.left} <-> {edge.right} ({conn_type})"


def _describe_edge_removed(edge: Edge) -> str:
    """Generate description for edge removed event."""
    return f"Connection removed: {edge.left} <-> {edge.right}"


def _describe_edge_changed(edge: Edge, changes: dict[str, dict[str, Any]]) -> str:
    """Generate description for edge changed event."""
    if len(changes) == 1:
        key = list(changes.keys())[0]
        if key == "speed":
            old_val = changes[key]["old"]
            new_val = changes[key]["new"]
            return (
                f"Connection {edge.left} <-> {edge.right} speed changed from {old_val} to {new_val}"
            )
        if key == "poe":
            new_val = changes[key]["new"]
            poe_state = "enabled" if new_val else "disabled"
            return f"Connection {edge.left} <-> {edge.right} PoE {poe_state}"
    return f"Connection {edge.left} <-> {edge.right} changed"


# --- Main comparison function ---


def compare_topologies(
    old_devices: list[Device],
    new_devices: list[Device],
    old_clients: list[dict[str, Any]] | None = None,
    new_clients: list[dict[str, Any]] | None = None,
    old_edges: list[Edge] | None = None,
    new_edges: list[Edge] | None = None,
    *,
    old_timestamp: str | None = None,
    new_timestamp: str | None = None,
) -> TopologyDiff:
    """Compare two topology snapshots and return structured change events.

    Args:
        old_devices: Devices from the previous snapshot.
        new_devices: Devices from the current snapshot.
        old_clients: Clients from the previous snapshot (optional).
        new_clients: Clients from the current snapshot (optional).
        old_edges: Edges from the previous snapshot (optional).
        new_edges: Edges from the current snapshot (optional).
        old_timestamp: ISO timestamp of old snapshot.
        new_timestamp: ISO timestamp of new snapshot.

    Returns:
        TopologyDiff containing all detected changes.
    """
    events: list[TopologyChangeEvent] = []
    timestamp = new_timestamp or datetime.now(UTC).isoformat()

    # Compare devices
    _compare_devices(old_devices, new_devices, events, timestamp)

    # Compare clients
    if old_clients is not None and new_clients is not None:
        _compare_clients(old_clients, new_clients, events, timestamp)

    # Compare edges
    if old_edges is not None and new_edges is not None:
        _compare_edges(old_edges, new_edges, events, timestamp)

    return TopologyDiff(
        events=events,
        old_timestamp=old_timestamp,
        new_timestamp=new_timestamp,
        summary=_build_summary(events),
    )


def _compare_devices(
    old_devices: list[Device],
    new_devices: list[Device],
    events: list[TopologyChangeEvent],
    timestamp: str,
) -> None:
    """Compare device lists and add events."""
    old_by_mac = {normalize_mac(d.mac): d for d in old_devices}
    new_by_mac = {normalize_mac(d.mac): d for d in new_devices}

    old_macs = set(old_by_mac.keys())
    new_macs = set(new_by_mac.keys())

    # Added devices
    for mac in sorted(new_macs - old_macs):
        device = new_by_mac[mac]
        events.append(
            TopologyChangeEvent(
                event_type="node_added",
                entity_type="device",
                identifier=mac,
                name=device.name,
                description=_describe_device_added(device),
                details=device_to_dict(device),
                timestamp=timestamp,
            )
        )

    # Removed devices
    for mac in sorted(old_macs - new_macs):
        device = old_by_mac[mac]
        events.append(
            TopologyChangeEvent(
                event_type="node_removed",
                entity_type="device",
                identifier=mac,
                name=device.name,
                description=_describe_device_removed(device),
                details=device_to_dict(device),
                timestamp=timestamp,
            )
        )

    # Changed devices
    for mac in sorted(old_macs & new_macs):
        old_device = old_by_mac[mac]
        new_device = new_by_mac[mac]
        old_props = _device_properties(old_device)
        new_props = _device_properties(new_device)
        changes = _compare_properties(old_props, new_props)
        if changes:
            events.append(
                TopologyChangeEvent(
                    event_type="node_changed",
                    entity_type="device",
                    identifier=mac,
                    name=new_device.name,
                    description=_describe_device_changed(new_device, changes),
                    details={"changes": changes},
                    timestamp=timestamp,
                )
            )


def _compare_clients(
    old_clients: list[dict[str, Any]],
    new_clients: list[dict[str, Any]],
    events: list[TopologyChangeEvent],
    timestamp: str,
) -> None:
    """Compare client lists and add events."""
    old_by_mac = {normalize_mac(c.get("mac", "")): c for c in old_clients if c.get("mac")}
    new_by_mac = {normalize_mac(c.get("mac", "")): c for c in new_clients if c.get("mac")}

    old_macs = set(old_by_mac.keys())
    new_macs = set(new_by_mac.keys())

    # Added clients
    for mac in sorted(new_macs - old_macs):
        client = new_by_mac[mac]
        events.append(
            TopologyChangeEvent(
                event_type="node_added",
                entity_type="client",
                identifier=mac,
                name=client.get("name") or client.get("hostname"),
                description=_describe_client_added(client),
                details=_client_properties(client),
                timestamp=timestamp,
            )
        )

    # Removed clients
    for mac in sorted(old_macs - new_macs):
        client = old_by_mac[mac]
        events.append(
            TopologyChangeEvent(
                event_type="node_removed",
                entity_type="client",
                identifier=mac,
                name=client.get("name") or client.get("hostname"),
                description=_describe_client_removed(client),
                details=_client_properties(client),
                timestamp=timestamp,
            )
        )

    # Changed clients
    for mac in sorted(old_macs & new_macs):
        old_client = old_by_mac[mac]
        new_client = new_by_mac[mac]
        old_props = _client_properties(old_client)
        new_props = _client_properties(new_client)
        changes = _compare_properties(old_props, new_props)
        if changes:
            events.append(
                TopologyChangeEvent(
                    event_type="node_changed",
                    entity_type="client",
                    identifier=mac,
                    name=new_client.get("name") or new_client.get("hostname"),
                    description=_describe_client_changed(new_client, changes),
                    details={"changes": changes},
                    timestamp=timestamp,
                )
            )


def _compare_edges(
    old_edges: list[Edge],
    new_edges: list[Edge],
    events: list[TopologyChangeEvent],
    timestamp: str,
) -> None:
    """Compare edge lists and add events."""
    old_by_key = {_edge_key(e): e for e in old_edges}
    new_by_key = {_edge_key(e): e for e in new_edges}

    old_keys = set(old_by_key.keys())
    new_keys = set(new_by_key.keys())

    # Added edges
    for key in sorted(new_keys - old_keys, key=lambda k: tuple(sorted(k))):
        edge = new_by_key[key]
        events.append(
            TopologyChangeEvent(
                event_type="edge_added",
                entity_type="device",  # Could be client edge, but entity_type is for filtering
                identifier=f"{edge.left}:{edge.right}",
                name=None,
                description=_describe_edge_added(edge),
                details=edge_to_dict(edge),
                timestamp=timestamp,
            )
        )

    # Removed edges
    for key in sorted(old_keys - new_keys, key=lambda k: tuple(sorted(k))):
        edge = old_by_key[key]
        events.append(
            TopologyChangeEvent(
                event_type="edge_removed",
                entity_type="device",
                identifier=f"{edge.left}:{edge.right}",
                name=None,
                description=_describe_edge_removed(edge),
                details=edge_to_dict(edge),
                timestamp=timestamp,
            )
        )

    # Changed edges
    for key in sorted(old_keys & new_keys, key=lambda k: tuple(sorted(k))):
        old_edge = old_by_key[key]
        new_edge = new_by_key[key]
        old_props = _edge_properties(old_edge)
        new_props = _edge_properties(new_edge)
        changes = _compare_properties(old_props, new_props)
        if changes:
            events.append(
                TopologyChangeEvent(
                    event_type="edge_changed",
                    entity_type="device",
                    identifier=f"{new_edge.left}:{new_edge.right}",
                    name=None,
                    description=_describe_edge_changed(new_edge, changes),
                    details={"changes": changes},
                    timestamp=timestamp,
                )
            )
