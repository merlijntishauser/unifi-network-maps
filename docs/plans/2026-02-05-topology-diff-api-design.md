# Topology Diff API Design

**Date**: 2026-02-05
**Issue**: [#21 - Feature: Topology diff API for change detection](https://github.com/merlijntishauser/unifi-network-maps/issues/21)
**Status**: Design approved

## Summary

Add a method to compare two topology snapshots and return structured change events, enabling the Home Assistant integration to detect and alert on network topology changes.

## Requirements

| Requirement | Decision |
|-------------|----------|
| Granularity | All properties (IP, hostname, signal, VLANs, connections, speeds, etc.) |
| Output format | Event-style list of change events |
| Serialization | JSON-serializable for persistence and MQTT transmission |
| Descriptions | Human-readable messages included for notifications |
| API location | Both standalone function and Topology method |
| State/History | Caller's responsibility; library provides snapshot serialization |

## Use Cases

1. **Device discovery**: New devices appearing on the network
2. **Device departure**: Devices going offline or being removed
3. **Connection changes**: Device moved to different port or AP
4. **VLAN changes**: Device membership changed
5. **Property changes**: IP, hostname, signal strength, speed changes

## Data Model

### TopologyChangeEvent

```python
@dataclass
class TopologyChangeEvent:
    """A single change detected between two topology snapshots."""

    event_type: str
    # One of: "node_added", "node_removed", "node_changed",
    #         "edge_added", "edge_removed", "edge_changed"

    entity_type: str
    # "device" or "client"

    identifier: str
    # MAC address - stable identifier across renames

    name: str | None
    # Human-readable name (from newer topology if changed)

    description: str
    # Human-readable message for notifications
    # e.g., "Device 'switch-1' appeared on network"
    # e.g., "Client 'laptop' moved from port 3 to port 7 on switch-1"

    details: dict[str, Any]
    # Event-specific payload (see below)

    timestamp: str | None
    # ISO timestamp if available from topology metadata

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        ...
```

### TopologyDiff

```python
@dataclass
class TopologyDiff:
    """Result of comparing two topology snapshots."""

    events: list[TopologyChangeEvent]
    # All detected changes

    old_timestamp: str | None
    new_timestamp: str | None
    # Timestamps from topology metadata if available

    summary: str
    # Human-readable summary
    # e.g., "3 devices added, 1 removed, 2 changed"

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        ...

    def to_json(self) -> str:
        """Serialize to JSON string."""
        ...

    def filter(self, event_types: set[str] | None = None,
               entity_types: set[str] | None = None) -> TopologyDiff:
        """Return filtered diff with only matching events."""
        ...
```

## Event Details by Type

### Node Events

| Event Type | Details Payload |
|------------|-----------------|
| `node_added` | Full node snapshot as dict |
| `node_removed` | Full node snapshot from old topology |
| `node_changed` | `{"changes": {"property": {"old": val, "new": val}, ...}}` |

Node properties tracked for changes:
- `name` - Device/client name
- `ip` - IP address
- `vlan` - VLAN ID
- `model` - Device model
- `type` - Device type classification
- `is_adopted` - Adoption status
- `is_online` - Online status (if detectable)
- `uplink_mac` - Connected to which device
- `uplink_port` - Connected on which port
- `signal` - Wireless signal strength (clients)
- `channel` - WiFi channel (clients)
- `satisfaction` - Client satisfaction score

### Edge Events

| Event Type | Details Payload |
|------------|-----------------|
| `edge_added` | `{"source": mac, "target": mac, "source_port": int|None, "target_port": int|None, "link_type": str}` |
| `edge_removed` | Same structure as added |
| `edge_changed` | `{"source": mac, "target": mac, "changes": {"port": {"old": 3, "new": 7}}}` |

Edge properties tracked:
- `source_port` - Port number on source device
- `target_port` - Port number on target device
- `link_type` - Type of connection (wired, wireless, uplink)
- `speed` - Link speed if available

## Public API

### Standalone Function

```python
from unifi_network_maps.model.diff import compare_topologies, TopologyDiff

diff: TopologyDiff = compare_topologies(old_topology, new_topology)

for event in diff.events:
    if event.event_type == "node_added":
        send_notification(f"New device: {event.description}")

# Serialize for storage or MQTT
json_data = diff.to_json()
```

### Topology Method

```python
from unifi_network_maps.model.topology import Topology

old_topology = Topology(...)
new_topology = Topology(...)

diff = old_topology.diff(new_topology)
# Equivalent to: compare_topologies(old_topology, new_topology)
```

### Filtering

```python
# Get only node changes
node_diff = diff.filter(event_types={"node_added", "node_removed", "node_changed"})

# Get only device events (not clients)
device_diff = diff.filter(entity_types={"device"})
```

## Example Output

```json
{
  "events": [
    {
      "event_type": "node_added",
      "entity_type": "client",
      "identifier": "aa:bb:cc:dd:ee:ff",
      "name": "iPhone-Merlijn",
      "description": "Client 'iPhone-Merlijn' connected to AP-Living via WiFi",
      "details": {
        "ip": "192.168.1.42",
        "vlan": 1,
        "type": "phone",
        "uplink_mac": "11:22:33:44:55:66",
        "signal": -45
      },
      "timestamp": "2026-02-05T10:30:00Z"
    },
    {
      "event_type": "node_changed",
      "entity_type": "client",
      "identifier": "ff:ee:dd:cc:bb:aa",
      "name": "laptop-work",
      "description": "Client 'laptop-work' changed VLAN from 10 to 20",
      "details": {
        "changes": {
          "vlan": {"old": 10, "new": 20}
        }
      },
      "timestamp": "2026-02-05T10:30:00Z"
    },
    {
      "event_type": "edge_changed",
      "entity_type": "device",
      "identifier": "aa:aa:aa:aa:aa:aa",
      "name": "switch-office",
      "description": "Device 'switch-office' moved from port 1 to port 24 on core-switch",
      "details": {
        "source": "bb:bb:bb:bb:bb:bb",
        "target": "aa:aa:aa:aa:aa:aa",
        "changes": {
          "source_port": {"old": 1, "new": 24}
        }
      },
      "timestamp": "2026-02-05T10:30:00Z"
    }
  ],
  "old_timestamp": "2026-02-05T10:00:00Z",
  "new_timestamp": "2026-02-05T10:30:00Z",
  "summary": "1 client added, 1 client changed, 1 connection changed"
}
```

## File Structure

```
src/unifi_network_maps/model/
├── topology.py          # Add .diff(), to_dict(), from_dict() methods
├── diff.py              # NEW: TopologyChangeEvent, TopologyDiff, compare_topologies()
├── snapshot.py          # NEW: Serialization helpers for Device, Client, Edge
```

## Implementation Notes

### Stable Identifiers

Use MAC address as the stable identifier for matching nodes across snapshots:
- Devices: `device.mac`
- Clients: `client.mac`

This handles renames gracefully - if a device is renamed, it's detected as a `node_changed` event with `name` in the changes, not as remove + add.

### Edge Matching

Edges are identified by their source and target MACs. Port changes on the same connection are `edge_changed`, while completely new connections are `edge_added`.

### Performance

For large networks (1000+ nodes), the diff algorithm should:
- Build MAC-indexed lookups O(n)
- Compare in single pass O(n)
- Total: O(n) time, O(n) space

### Optional: Diff Options

Future extension could add options parameter:

```python
diff = compare_topologies(old, new, options={
    "ignore_properties": {"signal", "satisfaction"},  # Skip noisy properties
    "include_offline": False,  # Skip offline device changes
})
```

This is not in initial scope but the design accommodates it.

## Testing Strategy

1. **Unit tests** for `compare_topologies()`:
   - Empty topologies
   - Identical topologies (no changes)
   - Node additions only
   - Node removals only
   - Node property changes
   - Edge additions/removals/changes
   - Mixed changes
   - Rename detection (same MAC, different name)

2. **Serialization tests**:
   - `to_dict()` produces valid JSON-serializable output
   - `to_json()` round-trips correctly
   - All event types serialize properly

3. **Description generation tests**:
   - Verify human-readable descriptions are accurate
   - Test edge cases (missing names, multiple changes)

## State Management and History

### Philosophy

The library provides **stateless comparison** - it compares two topology snapshots without managing persistence. The caller (e.g., Home Assistant integration) is responsible for:

1. **Storing snapshots**: Save topology state between polls
2. **Managing history**: Keep N snapshots for trend analysis
3. **Choosing storage**: File, database, in-memory, etc.

This separation keeps the library simple and gives integrations full control over their persistence strategy.

### Topology Serialization

To support persistence, `Topology` gets `to_dict()` and `from_dict()` methods:

```python
from unifi_network_maps.model.topology import Topology

# Save snapshot
topology = Topology(devices, clients, networks)
snapshot = topology.to_dict()
json.dump(snapshot, open("topology_2026-02-05.json", "w"))

# Load snapshot
snapshot = json.load(open("topology_2026-02-05.json"))
old_topology = Topology.from_dict(snapshot)

# Compare
diff = old_topology.diff(current_topology)
```

### Snapshot Format

```json
{
  "version": 1,
  "timestamp": "2026-02-05T10:00:00Z",
  "devices": [
    {
      "mac": "aa:bb:cc:dd:ee:ff",
      "name": "switch-1",
      "model": "USW-Pro-24-PoE",
      "type": "switch",
      "ip": "192.168.1.10",
      "ports": [...],
      "uplink": {...}
    }
  ],
  "clients": [
    {
      "mac": "11:22:33:44:55:66",
      "name": "laptop",
      "ip": "192.168.1.42",
      "vlan": 1,
      "uplink_mac": "aa:bb:cc:dd:ee:ff",
      "uplink_port": 3
    }
  ],
  "edges": [...]
}
```

### Example: Home Assistant Integration

```python
class UnifiTopologyCoordinator:
    def __init__(self, hass, config):
        self._previous_topology: Topology | None = None
        self._storage = Store(hass, 1, "unifi_network_maps_topology")

    async def _async_update_data(self):
        # Fetch current topology
        current = await self._fetch_topology()

        # Load previous from storage if first run
        if self._previous_topology is None:
            stored = await self._storage.async_load()
            if stored:
                self._previous_topology = Topology.from_dict(stored)

        # Compare and fire events
        if self._previous_topology:
            diff = self._previous_topology.diff(current)
            for event in diff.events:
                self.hass.bus.async_fire(
                    "unifi_network_topology_change",
                    event.to_dict()
                )

        # Persist for next comparison
        await self._storage.async_save(current.to_dict())
        self._previous_topology = current

        return current
```

## Migration / Breaking Changes

None - this is a new additive API.

## Dependencies

No new dependencies required. Uses only:
- `dataclasses` (stdlib)
- `json` (stdlib)
- Existing `Topology` model
