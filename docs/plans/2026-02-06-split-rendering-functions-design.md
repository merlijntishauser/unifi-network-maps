# Refactor: Split long rendering functions

Addresses [#29](https://github.com/merlijntishauser/unifi-network-maps/issues/29).

## Scope

Split `_render_wan_upstream()` (86 lines) and `_render_iso_node()` (114 lines).
`main()` (68 lines) is excluded — it's already well-factored with extracted
helpers; further splitting would create thin wrappers with little benefit.

## Changes

### `render/svg.py` — 3 extractions from `_render_wan_upstream()`

- `_wan_box_dimensions(label_lines, font_size)`: pure calculation of box size.
- `_render_wan_globe(lines, globe_cx, globe_cy, globe_r)`: globe SVG icon.
- `_render_wan_labels(lines, label_lines, ...)`: text label rendering.

Orchestration remains in `_render_wan_upstream()` (~35 lines).

### `render/svg_isometric.py` — 2 extractions from `_render_iso_node()`

- `_render_iso_node_icon(lines, ...)`: icon positioning with type-specific
  adjustments (AP lift, client offset, port label shift).
- `_render_iso_node_name(lines, ...)`: name label positioning (front face vs
  top face) and isometric transform.

Orchestration remains in `_render_iso_node()` (~50 lines).

## Out of scope

- `main()` in `cli/main.py` — already well-structured.
- Depth calculation and face rendering in `_render_iso_node()` — too small
  (8 and 12 lines) to benefit from extraction.
