# Edge VLAN Metadata Enhancement

**Issue**: [#20](https://github.com/merlijntishauser/unifi-network-maps/issues/20)
**Date**: 2026-02-02
**Status**: Approved

## Summary

Enhance edge metadata with VLAN information and visualize VLAN traffic flows in SVG output using striped multi-color edges.

## Goals

- Include VLAN/network segment information on edges in topology data
- Enable Home Assistant integration to visualize VLAN traffic flows
- Color-code edges by VLAN with distinct trunk vs access port styling
- Provide data attributes for dynamic styling by consumers

## Data Model Changes

### Edge Dataclass Extension

```python
@dataclass(frozen=True)
class Edge:
    left: str
    right: str
    label: str | None = None
    poe: bool = False
    wireless: bool = False
    speed: int | None = None
    channel: int | None = None
    # New fields:
    vlans: tuple[int, ...] = ()        # All VLANs configured on this link
    active_vlans: tuple[int, ...] = () # VLANs with current client traffic
    is_trunk: bool = False             # True if multiple VLANs configured
```

### PortInfo Extension

```python
@dataclass(frozen=True)
class PortInfo:
    # ... existing fields ...
    native_vlan: int | None = None      # Untagged/native VLAN
    tagged_vlans: tuple[int, ...] = ()  # Tagged VLANs allowed on trunk
```

## VLAN Data Sources

| Link Type | VLAN Source | Active Detection |
|-----------|-------------|------------------|
| Wired | Port `native_vlan` + `tagged_vlans` from `port_table` | Clients connected through port |
| Wireless | WLAN → Network → VLAN mapping | Clients on that SSID |

### Extraction Points

1. **Port VLAN config**: Extract from device `port_table` in `adapters/unifi.py`
2. **WLAN VLAN mapping**: Build lookup from `fetch_networks()` results
3. **Active detection**: Cross-reference client VLANs in `build_edges()`

## SVG Rendering

### Data Attributes

Every edge element includes VLAN metadata:

```xml
<path class="edge"
      data-vlans="10,20,30"
      data-active-vlans="10,20"
      data-trunk="true"
      d="M100,100 L200,200" />
```

### Striped Edge Visualization

Edges with active VLANs render as dashed segments with alternating colors:

```xml
<g class="edge-group" data-vlans="10,20,30" data-trunk="true">
  <path d="..." stroke="#ff6b6b" stroke-dasharray="20 40" stroke-dashoffset="0" />
  <path d="..." stroke="#4ecdc4" stroke-dasharray="20 40" stroke-dashoffset="-20" />
  <path d="..." stroke="#ffe66d" stroke-dasharray="20 40" stroke-dashoffset="-40" />
</g>
```

- **Access ports**: Single-color stripe (consistent style)
- **Trunk ports**: Multi-color stripes
- **Visual limit**: Only active VLANs shown; `--max-vlan-colors` caps density

## VLAN Color Mapping

### Theme Configuration

Users define VLAN colors in theme YAML:

```yaml
vlan_colors:
  1: "#6c757d"      # Default/management
  10: "#ff6b6b"     # IoT
  20: "#4ecdc4"     # Guest
  30: "#ffe66d"     # Trusted
```

### Auto-Generated Fallback

VLANs without explicit colors use golden angle HSL rotation:

```python
def vlan_color(vlan_id: int, theme_colors: dict[int, str]) -> str:
    if vlan_id in theme_colors:
        return theme_colors[vlan_id]
    hue = (vlan_id * 137) % 360  # Golden angle for distinct colors
    return f"hsl({hue}, 70%, 55%)"
```

## VLAN Legend

Optional via `--include-vlan-legend` flag.

- Lists VLANs active in the diagram
- Shows color swatch + VLAN ID + network name
- Positioned below device type legend
- Sorted by VLAN ID

## Mermaid Output

VLAN info appended to edge labels:

```
switch-1 ---|"Port 5 [V10,V20]"| ap-living-room;
switch-1 ---|"Port 3 [V30]"| camera-nvr;
```

Format rules:
- Only active VLANs shown
- Compact notation: `[V10]` single, `[V10,V20,V30]` multiple
- No suffix if no active VLANs

## JSON Output

Edge schema includes VLAN fields:

```json
{
  "left": "switch-1",
  "right": "ap-living-room",
  "label": "Port 5",
  "poe": true,
  "wireless": false,
  "speed": 1000,
  "vlans": [10, 20, 30],
  "active_vlans": [10, 20],
  "is_trunk": true
}
```

## CLI Interface

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--max-vlan-colors` | int | None | Limit VLAN colors shown on edges |
| `--include-vlan-legend` | flag | False | Add VLAN color legend to SVG |

### Affected Output Formats

| Format | VLAN Support |
|--------|--------------|
| `svg` / `svg-iso` | Full visualization (stripes, data attributes, optional legend) |
| `mermaid` | VLAN labels on edges |
| `json` | VLAN fields on edge objects |
| `mkdocs` | Inherits from embedded format |
| `lldp-md` | No change |

## Implementation Notes

### Files to Modify

1. `model/topology.py` - Edge dataclass, PortInfo, edge building logic
2. `adapters/unifi.py` - Port VLAN extraction, WLAN-VLAN mapping
3. `render/svg.py` - Striped edge rendering, data attributes
4. `render/svg_theme.py` - VLAN color resolution
5. `render/legend.py` - VLAN legend rendering
6. `render/mermaid.py` - Edge label formatting
7. `render/theme.py` - Theme loading for vlan_colors
8. `cli/args.py` - New CLI flags
9. `assets/themes/*.yaml` - Default vlan_colors

### Edge Cases

- Edges with no VLAN data: Render as current style (no stripes)
- Unknown VLANs: Auto-generate color, omit from legend name
- PoE + VLAN: Layer VLAN stripes, keep PoE indicator icon
- Wireless + VLAN: Dashed stripes (combine wireless dash with VLAN colors)