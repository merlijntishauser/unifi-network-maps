# Connection Quality Data Design

**Issue:** [#24 - Feature: Connection quality data (signal strength, negotiated speed)](https://github.com/merlijntishauser/unifi-network-maps/issues/24)

**Date:** 2026-02-05

**Status:** Approved

## Goal

Expose wireless signal strength and connection quality data in the JSON output for consumption by the Home Assistant integration.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary consumer | Home Assistant | HA needs structured data for sensors/attributes |
| Data location | Edge objects | Quality is tied to the AP-client connection |
| Fields included | All available + computed | Let HA decide what to use |
| Opt-in flag | No (always included) | Minimal payload increase, HA expects it |

## Data Model

New frozen dataclass in `model/connection.py`:

```python
@dataclass(frozen=True)
class ConnectionInfo:
    """Quality metrics for a wireless client connection."""

    signal_dbm: int | None = None        # RSSI (-30 to -90 typical)
    noise_dbm: int | None = None         # Background noise
    tx_rate_mbps: int | None = None      # Transmit rate
    rx_rate_mbps: int | None = None      # Receive rate
    satisfaction: int | None = None       # UniFi's 0-100 score
    quality: str | None = None           # Computed classification
```

The `Edge` dataclass gains a new field:

```python
connection: ConnectionInfo | None = None
```

## Quality Classification

Computed from `signal_dbm`:

| Quality | Signal Range |
|---------|--------------|
| excellent | > -50 dBm |
| good | -50 to -65 dBm |
| fair | -65 to -75 dBm |
| poor | < -75 dBm |

## JSON Output

```json
{
  "edges": [
    {
      "left": "AP Living Room",
      "right": "iPhone",
      "wireless": true,
      "channel": 36,
      "connection": {
        "signal_dbm": -65,
        "noise_dbm": -95,
        "tx_rate_mbps": 866,
        "rx_rate_mbps": 866,
        "satisfaction": 98,
        "quality": "good"
      }
    }
  ]
}
```

- `connection` is `null` for wired clients and device-to-device edges
- Fields within `connection` can be `null` if the API didn't provide them

## Implementation

### Files to Create

| File | Purpose |
|------|---------|
| `src/unifi_network_maps/model/connection.py` | `ConnectionInfo` dataclass + `classify_signal_quality()` |
| `tests/test_connection.py` | Unit tests for connection quality |

### Files to Modify

| File | Change |
|------|--------|
| `model/topology.py` | Add `connection` field to `Edge` |
| `model/clients.py` | Add `_extract_connection_info()`, attach to edges |
| `model/mock.py` | Generate signal/noise/satisfaction for wireless clients |
| `model/snapshot.py` | Serialize/deserialize `ConnectionInfo` |
| `tests/test_clients.py` | Integration tests for connection extraction |

## Testing

### Unit Tests

- `test_classify_signal_quality` - Threshold boundary verification
- `test_extract_connection_info_wireless` - Field extraction from wireless client
- `test_extract_connection_info_wired` - Returns `None` for wired
- `test_edge_with_connection_info` - Edge accepts connection field

### Integration Tests

- Verify `build_client_edges` attaches `ConnectionInfo` to wireless edges

### Contract Tests

- Add fixture with signal/noise/satisfaction fields
- Verify extraction matches expected structure

## Out of Scope

- SVG visual rendering (color-coded edges, quality badges)
- CLI flags for opt-in/opt-out
- Wired connection negotiated speed (separate feature)
