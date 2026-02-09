# Design: Decompose svg.py to reach MI grade B

## Problem

`radon mi` reports `svg.py` at maintainability index C (7.58). The MI formula is
`171 - 5.2*ln(V) - 0.23*CC - 16.2*ln(LLOC)`, where the LLOC term alone accounts
for 64% of the penalty. At 609 LLOC the file is too large for grade B regardless
of cyclomatic complexity.

Target: MI >= 10 (grade B), which requires LLOC <= ~500.

## Approach

Extract three cohesive subsystems into sibling modules. No public API changes.

### Module structure

```
render/
  svg.py           ~300 LLOC  Orchestrator: render_svg, render_dual, node rendering
  svg_layout.py    ~210 LLOC  Tree layout + grouped layout
  svg_wan.py       ~120 LLOC  WAN upstream + group boundary rendering
  svg_edges.py     ~200 LLOC  Edge rendering + label recording
```

### svg_layout.py

Exports: `GroupBounds`, `_layout_nodes`, `_layout_grouped_nodes`,
`_offset_positions`, `_layout_nodeset`.

Internal helpers moved wholesale: `_tree_layout_indices`, `_build_children_maps`,
`_sort_key_for_nodes`, `_sort_children`, `_resolve_roots`, `_layout_positions`,
`_assign_nodes_to_groups`, `_resolve_group_order`, `_filter_edges_for_group`,
`_layout_single_group`, `_compute_group_bounds`.

### svg_wan.py

Exports: `_render_wan_upstream`, `_apply_wan_offset`, `_find_gateway_position`,
`_render_group_boundaries`, `_vlan_group_colors`.

Internal helpers: `_wan_box_dimensions`, `_render_wan_globe`, `_render_wan_labels`.

### svg_edges.py

Exports: `_render_svg_edges`.

Internal helpers: `_vlan_data_attrs`, `_edge_opacity`,
`_render_vlan_endpoint_markers`, `_render_vlan_striped_edge`,
`_compute_elbow_path`, `_render_poe_icon`, `_render_standard_edge`,
`_render_single_edge`, `_record_client_label`, `_record_infra_label`,
`_record_edge_labels`.

### Stays in svg.py

`SvgOptions`, `_build_font_style`, `_svg_style_block`, `_compute_svg_layout`,
`render_svg`, `_render_svg_nodes`, `_build_node_to_group_map`,
`_svg_node_group_attrs`, `_groups_from_vlan_node_map`, `render_dual`.

## Verification

- `radon mi src/unifi_network_maps/render/svg.py -s` reports B
- `radon cc src/unifi_network_maps/render/svg.py -s -n C` reports 0
- `ruff check . && ruff format --check .`
- `pyright` 0 errors
- `pytest` all pass
- `behave` all pass
- `make smoketest-mock && make smoketest-validate`
