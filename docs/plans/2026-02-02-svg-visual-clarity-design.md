# SVG Visual Clarity Improvements

**Date:** 2026-02-02
**Status:** Approved
**Version Target:** 1.5.0

## Overview

Comprehensive visual refresh for SVG network diagrams focusing on node consistency, VLAN visibility, and diagram legibility when many clients are present.

## Problem Statement

1. **Node depth inconsistency:** Isometric nodes render as flat diamonds (`node_depth = 0.0`). Nodes with port labels have a raised label tile, creating visual inconsistency.

2. **VLAN edge clarity:** Striped dash patterns for VLAN-colored edges are hard to distinguish when edges overlap.

3. **Diagram clutter:** Many clients create visual noise that obscures core network topology.

## Design Decisions

| Aspect | Approach |
|--------|----------|
| Node depth | Consistent small depth for all nodes |
| VLAN edges | Glow effect + colored endpoint markers |
| Legibility | Client clustering via CLI flag + opacity layering |

## Implementation Details

### 1. Node Depth Consistency

**Change:** In `_render_iso_node()` (svg.py), set consistent depth:

```python
node_depth = layout.tile_height * 0.15  # ~20px at default settings
```

**Effect:** All nodes appear as 3D boxes instead of flat diamonds.

**Files:** `src/unifi_network_maps/render/svg.py`

---

### 2. Edge Glow Effect

**Change:** Render a blurred background path before striped segments for VLAN edges.

```python
if len(vlans) > 0:
    glow_color = theme.vlan_color(vlans[0])
    glow_width = base_width * 3
    lines.append(
        f'<path d="{path}" stroke="{glow_color}" stroke-width="{glow_width}" '
        f'fill="none" opacity="0.25" filter="url(#edge-glow)"/>'
    )
```

**SVG filter definition:**
```xml
<filter id="edge-glow" x="-50%" y="-50%" width="200%" height="200%">
  <feGaussianBlur stdDeviation="4" result="blur"/>
</filter>
```

**Effect:** VLAN edges have a soft colored halo drawing attention.

**Files:** `src/unifi_network_maps/render/svg.py`, `src/unifi_network_maps/render/svg_theme.py`

---

### 3. VLAN Endpoint Markers

**Change:** Render small colored squares at edge endpoints showing active VLANs.

```python
def _render_vlan_endpoint_markers(
    lines: list[str],
    x: float,
    y: float,
    vlans: tuple[int, ...],
    theme: SvgTheme,
    marker_size: int = 6,
) -> None:
    for i, vlan_id in enumerate(vlans[:4]):  # Max 4 markers
        color = theme.vlan_color(vlan_id)
        marker_y = y + (i * (marker_size + 2))
        lines.append(
            f'<rect x="{x}" y="{marker_y}" width="{marker_size}" '
            f'height="{marker_size}" fill="{color}" stroke="#fff" '
            f'stroke-width="0.5" rx="1" data-vlan="{vlan_id}">'
            f'<title>VLAN {vlan_id}</title></rect>'
        )
```

**Effect:** Small colored squares near nodes show which VLANs are active.

**Files:** `src/unifi_network_maps/render/svg.py`

---

### 4. Client Clustering

**CLI flag:**
```python
parser.add_argument(
    "--collapse-clients",
    action="store_true",
    help="Group clients by uplink device into cluster nodes with count badges",
)
```

**Topology transformation:**
```python
def collapse_client_edges(
    edges: list[Edge],
    node_types: dict[str, str],
) -> tuple[list[Edge], dict[str, int]]:
    client_counts: dict[str, int] = {}
    collapsed_edges: list[Edge] = []

    for edge in edges:
        if node_types.get(edge.right) == "client":
            client_counts[edge.left] = client_counts.get(edge.left, 0) + 1
        else:
            collapsed_edges.append(edge)

    for device_name, count in client_counts.items():
        cluster_name = f"{device_name} ({count} clients)"
        collapsed_edges.append(Edge(left=device_name, right=cluster_name))
        node_types[cluster_name] = "client_cluster"

    return collapsed_edges, client_counts
```

**Effect:** Clients grouped into single cluster node with count badge.

**Files:** `src/unifi_network_maps/cli/args.py`, `src/unifi_network_maps/model/topology.py`, `src/unifi_network_maps/render/svg.py`

---

### 5. Client Edge Opacity

**Change:** Apply reduced opacity to client edges:

```python
def _edge_opacity(node_types: dict[str, str], edge: Edge) -> float:
    left_type = node_types.get(edge.left, "other")
    right_type = node_types.get(edge.right, "other")

    if right_type == "client" or left_type == "client":
        return 0.5
    return 1.0
```

**Effect:** Infrastructure edges dominate visually; client edges recede.

**Files:** `src/unifi_network_maps/render/svg.py`

---

## Implementation Order

1. Node depth consistency (low complexity)
2. Client edge opacity (low complexity)
3. Edge glow effect (medium complexity)
4. VLAN endpoint markers (medium complexity)
5. Client clustering (medium complexity)
6. Create HA integration GitHub issue

## Breaking Changes for unifi-network-maps-ha

1. **New `--collapse-clients` flag** - Consider exposing as HA config option
2. **New node type: `client_cluster`** - Add CSS styling
3. **New SVG filter: `#edge-glow`** - No action needed
4. **VLAN endpoint markers** - New elements with `data-vlan` attribute

## Testing Strategy

- Update visual regression baselines after each feature
- Run `make smoketest-mock` to verify output structure
- Manual review of `network_vlan_all_clients_iso.svg`

## Version

These changes warrant a minor version bump: **1.4.x → 1.5.0**
