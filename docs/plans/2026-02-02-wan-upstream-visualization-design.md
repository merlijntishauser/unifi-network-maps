# WAN Upstream Visualization Design

**Date:** 2026-02-02
**Status:** Approved

## Overview

Add visual representation of WAN/Internet upstream connection above the gateway node, including a globe icon and WAN interface information.

## Requirements

1. Display floating globe icon above gateway to represent Internet/WAN
2. Show WAN port information (speed, IP address)
3. Support dual WAN interfaces
4. Show disabled/enabled status for each WAN interface
5. Allow CLI override for ISP-provided speed and label

## Visual Design

### Single WAN

```
       🌐
   KPN Fiber
Link 10G / ISP 1G ↓↑
  85.145.111.204
```

### Dual WAN (both active)

```
       🌐
   WAN1: KPN Fiber (1G ↓↑) ●
   WAN2: Backup 4G (500M ↓↑) ●
```

### Dual WAN (one disabled)

```
       🌐
   WAN1: KPN Fiber (1G ↓↑) ●
   WAN2: Backup 4G (disabled) ○
```

## CLI Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--wan-speed` | WAN1 ISP provisioned speed | `"1 Gbps ↓↑"` |
| `--wan-label` | WAN1 ISP/connection name | `"KPN Fiber"` |
| `--wan2-speed` | WAN2 ISP provisioned speed | `"500 Mbps ↓↑"` |
| `--wan2-label` | WAN2 ISP/connection name | `"Backup 4G"` |

## Display Logic

| Flags provided | Display |
|----------------|---------|
| None | Link speed from API + IP |
| `--wan-speed` only | `Link: 10G / ISP: 1G ↓↑` + IP |
| `--wan-label` only | Label + link speed + IP |
| Both flags | Label + `Link: 10G / ISP: 1G ↓↑` + IP |

## Data Sources

| Info | Source | Fallback |
|------|--------|----------|
| WAN IP | Gateway device `ip` field | Omit |
| Link Speed | Port table `speed` field for WAN port | Omit |
| ISP Speed | `--wan-speed` CLI flag | Omit |
| ISP Name | `--wan-label` CLI flag | Omit |
| Port Status | Port `speed > 0` = active | Assume active |

### WAN Port Identification

- WAN1: Typically eth0/Port 1 on UniFi gateways
- WAN2: Typically eth8/Port 9 on UDM Pro (varies by model)
- Detection: Check port name contains "WAN" or is first port with no native_vlan

## Visual Implementation

### Globe Icon

- Flat 2D icon (not on isometric tile)
- Positioned ~1.5 grid units "north" of gateway in isometric projection
- Size: ~80x80px, similar to device icons
- Visually distinct from LAN devices

### Label Rendering

- Isometric text transform (30° rotation + skew) matching node labels
- Smaller font for secondary info (IP address)
- Status indicators: ● (green) active, ○ (gray) disabled

### SVG Structure

```xml
<g class="wan-upstream" data-gateway="FiberDream">
  <image href="globe.svg" x="..." y="..." width="80" height="80"/>
  <text class="wan-label">KPN Fiber</text>
  <text class="wan-speed">Link 10G / ISP 1G ↓↑</text>
  <text class="wan-ip">85.145.111.204</text>
</g>
```

## Implementation

### Files to Modify

| File | Changes |
|------|---------|
| `cli/args.py` | Add WAN CLI flags |
| `model/topology.py` | Add `WanInfo` dataclass, extract WAN port data |
| `render/svg.py` | Add `_render_wan_upstream()` for orthogonal view |
| `render/svg.py` | Add `_render_iso_wan_upstream()` for isometric view |
| `assets/icons/` | Add `globe.svg` icon |
| `assets/icons/isometric/` | Add `globe.svg` (same flat icon) |

### Data Model

```python
@dataclass(frozen=True)
class WanInterface:
    port_idx: int
    link_speed: int | None      # From API (Mbps)
    ip_address: str | None      # Public IP
    enabled: bool               # Port up/down
    label: str | None           # From CLI flag
    isp_speed: str | None       # From CLI flag

@dataclass(frozen=True)
class WanInfo:
    wan1: WanInterface | None
    wan2: WanInterface | None
```

## Breaking Changes for unifi-network-maps-ha

1. **New CLI flags** - Expose as HA config options:
   - `wan_speed`, `wan_label`, `wan2_speed`, `wan2_label`
2. **New SVG elements** - Globe icon and WAN labels added above gateway
3. **New CSS classes** - `.wan-upstream`, `.wan-label`, `.wan-speed`, `.wan-ip`
4. **New data attributes** - `data-gateway` on WAN group element

## Testing

- Update visual regression baselines after implementation
- Test with single WAN and dual WAN configurations
- Test with all combinations of CLI flags
- Verify positioning in both orthogonal and isometric views
