# Plan: Dual SVG rendering function (#35)

## Context

The HA integration needs to serve both a physical topology SVG and a VLAN-grouped SVG for instant switching in the frontend. Without a dual render function, it would need to call the UniFi API twice or manually orchestrate two separate render calls with shared topology state.

Depends on #34 (VLAN-based grouping layout mode), which is now merged.

## API

```python
def render_dual(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    vlan_names: dict[int, str] | None = None,
    vlan_node_map: dict[str, int | None] | None = None,
    wan_info: WanInfo | None = None,
    isometric: bool = False,
) -> dict[str, str | None]:
    """Render both physical and VLAN-grouped SVGs from shared topology data.

    Returns {"physical": svg_str, "vlan": svg_str_or_none}.
    """
```

### Parameters

- `edges`, `node_types`, `options`, `theme`, `wan_info` -- same inputs as `render_svg()`. The caller does its own data prep (topology building, client edges, edge enrichment).
- `vlan_names` -- maps VLAN ID to human-readable name (e.g. `{1: "LAN", 10: "IoT"}`). Used when deriving VLAN groups from edges.
- `vlan_node_map` -- optional pre-computed node-to-VLAN mapping. When provided, used directly instead of deriving from edges. When `None`, falls back to `group_nodes_by_vlan(edges, vlan_names)`.
- `isometric` -- when `True`, uses `render_svg_isometric` for both outputs instead of `render_svg`.

### Return value

`{"physical": svg_str, "vlan": svg_str_or_none}` where `"vlan"` is `None` when no VLAN data is available (empty `vlan_names` and no `vlan_node_map`).

## Implementation

### Internal flow

1. Build physical `SvgOptions` with `layout_mode="physical"` (preserving width/height/other settings from input options).
2. Call `render_svg` or `render_svg_isometric` (based on `isometric` flag) to produce the physical SVG.
3. Build VLAN groups:
   - If `vlan_node_map` is provided, convert it to `(groups, group_order, group_vlan_ids)` via a helper `_groups_from_vlan_node_map()`.
   - Otherwise, call `group_nodes_by_vlan(edges, vlan_names)`.
4. If no VLAN groups were produced, return `{"physical": physical_svg, "vlan": None}`.
5. Build grouped `SvgOptions` with `layout_mode="grouped"`.
6. Call `render_svg` or `render_svg_isometric` with the VLAN groups, `group_order`, and `group_vlan_ids`.
7. Return `{"physical": physical_svg, "vlan": vlan_svg}`.

### Helper: `_groups_from_vlan_node_map`

Converts a `dict[str, int | None]` (node name to VLAN ID) into the same `(groups, group_order, group_vlan_ids)` tuple that `group_nodes_by_vlan` returns:

```python
def _groups_from_vlan_node_map(
    vlan_node_map: dict[str, int | None],
    vlan_names: dict[int, str] | None = None,
) -> tuple[dict[str, list[str]], list[str], dict[str, int]]:
```

- Nodes with `None` VLAN go into "Unassigned"
- Group names use `vlan_names` lookup, falling back to `"VLAN {id}"`
- Group order: sorted by VLAN ID ascending, "Unassigned" last

## Files to modify

| File | Change |
|------|--------|
| `src/unifi_network_maps/render/svg.py` | Add `render_dual()` and `_groups_from_vlan_node_map()` |
| `src/unifi_network_maps/render/__init__.py` | Re-export `render_dual` |
| `tests/test_render_dual.py` (new) | Unit tests |

## Testing

- Physical SVG matches output of standalone `render_svg` call with same inputs
- VLAN SVG contains group boundaries with VLAN names
- Empty `vlan_names` + no `vlan_node_map` returns `None` for `"vlan"` key
- `vlan_node_map` override produces correct grouping (groups match the map)
- `isometric=True` produces isometric output for both SVGs
- Both SVGs contain the same node set

## Verification

- `ruff check . && ruff format --check .`
- `pyright`
- `pytest`
- `behave`
- `make smoketest-mock && make smoketest-validate`
