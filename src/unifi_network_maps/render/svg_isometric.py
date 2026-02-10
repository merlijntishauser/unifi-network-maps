"""Isometric SVG rendering for network diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape as _escape_html

from ..model.topology import Edge, WanInfo
from .svg_icons import _build_decal_colors, _load_isometric_icons
from .svg_iso_edges import _render_iso_edges
from .svg_iso_geometry import IsoLayout, _iso_project, _iso_project_center
from .svg_iso_nodes import _render_iso_nodes
from .svg_labels import (
    _build_wan_label_lines,
    _escape_text,
)
from .svg_layout import _build_node_to_group_map, _resolve_group_order
from .svg_theme import DEFAULT_THEME, SvgOptions, SvgTheme, _svg_style_block, svg_defs
from .svg_wan import _vlan_group_colors

# Re-export IsoLayout for external consumers
__all__ = ["IsoLayout", "render_svg_isometric"]

# Isometric layout constants (module-level for discoverability)
_ISO_NW_PADDING = 300  # North-west padding for iso layout
_ISO_VIEWPORT_EXPAND = 400  # Viewport expansion around content
_ISO_GRID_EXTENT_PAD = 36  # Grid extent padding beyond content
_ISO_GROUP_LABEL_SIZE = 48  # Font size for group boundary labels
_ISO_PERSPECTIVE_ANGLE = 30  # Isometric perspective angle in degrees


@dataclass(frozen=True)
class IsoLayoutPositions:
    layout: IsoLayout
    grid_positions: dict[str, tuple[float, float]]
    positions: dict[str, tuple[float, float]]
    width: float
    height: float
    offset_x: float
    offset_y: float


def _iso_layout(options: SvgOptions) -> IsoLayout:
    tile_width = options.node_width * 1.5
    iso_angle = math.radians(30.0)
    tile_height = tile_width * math.tan(iso_angle)
    step_width = tile_width
    step_height = tile_height
    grid_spacing_x = max(2, 1 + int(round(options.h_gap / max(tile_width, 1))))
    grid_spacing_y = max(2, 1 + int(round(options.v_gap / max(tile_height, 1))))
    padding = float(options.padding)
    tile_y_offset = tile_height / 2
    extra_pad = max(12.0, tile_width * 0.35)
    return IsoLayout(
        iso_angle=iso_angle,
        tile_width=tile_width,
        tile_height=tile_height,
        step_width=step_width,
        step_height=step_height,
        grid_spacing_x=grid_spacing_x,
        grid_spacing_y=grid_spacing_y,
        padding=padding,
        tile_y_offset=tile_y_offset,
        extra_pad=extra_pad,
    )


def _iso_layout_positions(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
) -> IsoLayoutPositions:
    from .svg_layout import _tree_layout_indices

    layout = _iso_layout(options)
    positions_index, levels = _tree_layout_indices(edges, node_types)
    grid_positions: dict[str, tuple[float, float]] = {}
    positions: dict[str, tuple[float, float]] = {}
    for name, idx in positions_index.items():
        level = levels.get(name, 0)
        gx = round(idx * layout.grid_spacing_x)
        gy = round(float(level) * layout.grid_spacing_y)
        grid_positions[name] = (float(gx), float(gy))
        iso_x, iso_y = _iso_project_center(layout, float(gx), float(gy))
        positions[name] = (iso_x, iso_y)
    if positions:
        min_x = min(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        max_x = max(x for x, _ in positions.values())
        max_y = max(y for _, y in positions.values())
    else:
        min_x = min_y = 0.0
        max_x = max_y = 0.0
    offset_x = -min_x + layout.padding + _ISO_NW_PADDING
    offset_y = -min_y + layout.padding + layout.tile_y_offset + _ISO_NW_PADDING
    for name, (x, y) in positions.items():
        positions[name] = (x + offset_x, y + offset_y)
    # Expand viewport to show more of the grid
    viewport_expand = _ISO_VIEWPORT_EXPAND
    width = (
        max_x
        - min_x
        + layout.tile_width
        + layout.padding * 2
        + layout.extra_pad
        + viewport_expand
        + _ISO_NW_PADDING
    )
    height = (
        max_y
        - min_y
        + layout.tile_height
        + layout.padding * 2
        + layout.tile_y_offset
        + layout.extra_pad
        + viewport_expand
        + _ISO_NW_PADDING
    )
    return IsoLayoutPositions(
        layout=layout,
        grid_positions=grid_positions,
        positions=positions,
        width=width,
        height=height,
        offset_x=offset_x,
        offset_y=offset_y,
    )


def _iso_grid_lines(
    grid_positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    grid_color: str = "#efefef",
) -> list[str]:
    if not grid_positions:
        return []
    min_gx = min(gx for gx, _ in grid_positions.values())
    max_gx = max(gx for gx, _ in grid_positions.values())
    min_gy = min(gy for _, gy in grid_positions.values())
    max_gy = max(gy for _, gy in grid_positions.values())
    gx_start = int(math.floor(min_gx)) - _ISO_GRID_EXTENT_PAD
    gx_end = int(math.ceil(max_gx)) + _ISO_GRID_EXTENT_PAD
    gy_start = int(math.floor(min_gy)) - _ISO_GRID_EXTENT_PAD
    gy_end = int(math.ceil(max_gy)) + _ISO_GRID_EXTENT_PAD
    grid_lines: list[str] = []
    for gx in range(gx_start, gx_end + 1):
        x1, y1 = _iso_project(layout, float(gx), float(gy_start))
        x2, y2 = _iso_project(layout, float(gx), float(gy_end))
        x1 += layout.padding
        y1 += layout.padding
        x2 += layout.padding
        y2 += layout.padding
        grid_lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{grid_color}" stroke-width="0.6"/>'
        )
    for gy in range(gy_start, gy_end + 1):
        x1, y1 = _iso_project(layout, float(gx_start), float(gy))
        x2, y2 = _iso_project(layout, float(gx_end), float(gy))
        x1 += layout.padding
        y1 += layout.padding
        x2 += layout.padding
        y2 += layout.padding
        grid_lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{grid_color}" stroke-width="0.6"/>'
        )
    return grid_lines


def _render_iso_wan_upstream(
    lines: list[str],
    wan_info: WanInfo,
    gateway_position: tuple[float, float],
    layout: IsoLayout,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    """Render WAN upstream visualization (isometric view)."""
    gx, gy = gateway_position
    tile_w = layout.tile_width
    tile_h = layout.tile_height

    # Build label lines to calculate box size
    label_lines = _build_wan_label_lines(wan_info)
    font_size = max(options.font_size - 1, 8)

    # Calculate box dimensions based on content
    globe_size = 40
    padding = 12
    line_height = font_size + 4
    max_text_width = max((len(line) for line in label_lines), default=10) * font_size * 0.55
    box_width = max(globe_size + padding * 2, max_text_width + padding * 2)
    box_height = globe_size + len(label_lines) * line_height + padding * 3

    # Position box to the east (right side) of the gateway
    # Move along the isometric NE direction (slope ~0.5 for parallel grid lines)
    box_x = gx + tile_w + 60
    # Position so link runs parallel to isometric grid (y offset follows NE slope)
    box_y = gy - tile_h / 2 - box_height / 2 + 38

    # Connection point on gateway (east edge of tile)
    gateway_connect_x = gx + tile_w * 0.75
    gateway_connect_y = gy + tile_h * 0.25

    # Connection point on box (left edge, middle)
    box_connect_x = box_x
    box_connect_y = box_y + box_height / 2

    lines.append('<g class="wan-upstream">')

    # Draw connector line from gateway to box
    lines.append(
        f'<path d="M {gateway_connect_x} {gateway_connect_y} '
        f'L {box_connect_x} {box_connect_y}" '
        f'stroke="#0288d1" stroke-width="3" fill="none" '
        f'stroke-linecap="round" opacity="0.8"/>'
    )

    # Draw bounding box with rounded corners
    lines.append(
        f'<rect x="{box_x}" y="{box_y}" width="{box_width}" height="{box_height}" '
        f'rx="8" ry="8" fill="{theme.wan_background}" stroke="{theme.wan_globe[1]}" stroke-width="2"/>'
    )

    # Draw globe icon inline with gradient fill
    globe_cx = box_x + box_width / 2
    globe_cy = box_y + padding + globe_size / 2
    globe_r = globe_size / 2 - 2
    lines.append(f'<g transform="translate({globe_cx}, {globe_cy})">')
    # Globe circle
    lines.append(
        f'<circle cx="0" cy="0" r="{globe_r}" fill="none" '
        f'stroke="url(#iso-globe)" stroke-width="2"/>'
    )
    # Vertical ellipse (meridian)
    lines.append(
        f'<ellipse cx="0" cy="0" rx="{globe_r * 0.35}" ry="{globe_r}" '
        f'fill="none" stroke="url(#iso-globe)" stroke-width="1.5"/>'
    )
    # Horizontal line (equator)
    lines.append(
        f'<line x1="{-globe_r}" y1="0" x2="{globe_r}" y2="0" '
        f'stroke="url(#iso-globe)" stroke-width="1.5"/>'
    )
    # Latitude lines
    lines.append(
        f'<ellipse cx="0" cy="{-globe_r * 0.5}" rx="{globe_r * 0.87}" ry="{globe_r * 0.2}" '
        f'fill="none" stroke="url(#iso-globe)" stroke-width="1"/>'
    )
    lines.append(
        f'<ellipse cx="0" cy="{globe_r * 0.5}" rx="{globe_r * 0.87}" ry="{globe_r * 0.2}" '
        f'fill="none" stroke="url(#iso-globe)" stroke-width="1"/>'
    )
    lines.append("</g>")

    # Render label lines
    text_x = box_x + box_width / 2
    text_y = box_y + padding + globe_size + padding + font_size
    for i, label_text in enumerate(label_lines):
        y = text_y + i * line_height
        lines.append(
            f'<text x="{text_x}" y="{y}" text-anchor="middle" '
            f'fill="{theme.text_primary}" font-size="{font_size}">'
            f"{_escape_text(label_text)}</text>"
        )

    lines.append("</g>")


@dataclass(frozen=True)
class IsoGroupBounds:
    name: str
    points: list[tuple[float, float]]  # 4 corners of the parallelogram
    label_x: float
    label_y: float


def _compute_iso_group_bounds(
    grid_positions: dict[str, tuple[float, float]],
    groups: dict[str, list[str]],
    group_order: list[str] | None,
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    options: SvgOptions,
) -> list[IsoGroupBounds]:
    """Compute isometric group bounds as parallelograms aligned with grid."""
    ordered_groups = _resolve_group_order(groups, group_order)
    node_to_group = _build_node_to_group_map(groups)
    bounds_list: list[IsoGroupBounds] = []
    # Convert screen padding to grid units
    padding = options.group_padding / layout.step_width + 0.5

    for group_name in ordered_groups:
        group_grid = {
            n: pos for n, pos in grid_positions.items() if node_to_group.get(n) == group_name
        }
        if not group_grid:
            continue
        bounds = _iso_group_parallelogram(
            group_name, group_grid, layout, offset_x, offset_y, padding
        )
        bounds_list.append(bounds)
    return bounds_list


def _iso_group_parallelogram(
    name: str,
    group_grid: dict[str, tuple[float, float]],
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    padding: float,
) -> IsoGroupBounds:
    """Create isometric parallelogram bounds from grid positions."""
    gxs = [gx for gx, _ in group_grid.values()]
    gys = [gy for _, gy in group_grid.values()]

    is_single_node = len(group_grid) == 1
    if is_single_node:
        # For single-node groups: boundary centered around the node
        # Shift to align with node's visual center
        node_half = 0.8  # Half-size of boundary in grid units
        center_gx = min(gxs) + 1.45  # Tuned for visual centering
        center_gy = min(gys) + 0.45
        min_gx = center_gx - node_half
        max_gx = center_gx + node_half
        min_gy = center_gy - node_half
        max_gy = center_gy + node_half
    else:
        # For multi-node groups: use grid spacing with padding
        min_gx = min(gxs) - padding
        max_gx = max(gxs) + layout.grid_spacing_x + padding
        min_gy = min(gys) - padding
        max_gy = max(gys) + layout.grid_spacing_y + padding

    # Project grid corners to screen coordinates
    corners_grid = [
        (min_gx, min_gy),  # top
        (max_gx, min_gy),  # right
        (max_gx, max_gy),  # bottom
        (min_gx, max_gy),  # left
    ]
    points = [
        (
            _iso_project(layout, gx, gy)[0] + offset_x,
            _iso_project(layout, gx, gy)[1] + offset_y,
        )
        for gx, gy in corners_grid
    ]

    # Position label at the top corner, offset inward along the right edge
    top_x, top_y = points[0]
    right_x, right_y = points[1]
    label_x = top_x + (right_x - top_x) * 0.15 - 30  # Shifted NW
    label_y = top_y + (right_y - top_y) * 0.15 - 20
    return IsoGroupBounds(name=name, points=points, label_x=label_x, label_y=label_y)


def _render_iso_group_boundaries(
    lines: list[str],
    bounds_list: list[IsoGroupBounds],
    theme: SvgTheme,
    *,
    group_vlan_ids: dict[str, int] | None = None,
) -> None:
    """Render isometric group boundaries as parallelograms."""
    label_size = _ISO_GROUP_LABEL_SIZE
    iso_angle = _ISO_PERSPECTIVE_ANGLE
    for bounds in bounds_list:
        group_attr = _escape_html(bounds.name, quote=True)
        fill, stroke = _vlan_group_colors(bounds.name, theme, group_vlan_ids)
        points_str = " ".join(f"{x},{y}" for x, y in bounds.points)
        lines.append(f'<g class="network-group" data-group-name="{group_attr}">')
        lines.append(
            f'<polygon class="group-boundary" points="{points_str}" '
            f'fill="{fill}" fill-opacity="0.35" '
            f'stroke="{stroke}" stroke-width="{theme.group_stroke_width}"/>'
        )
        label_text = _escape_text(bounds.name.capitalize())
        lx, ly = bounds.label_x, bounds.label_y
        # Isometric transform: rotate + skew to follow 30deg perspective
        label_transform = (
            f"translate({lx} {ly}) rotate({iso_angle}) skewX({iso_angle}) translate({-lx} {-ly})"
        )
        # Text with thin outline for readability
        lines.append(
            f'<text class="group-label" x="{lx}" y="{ly}" '
            f'font-size="{label_size}" font-weight="bold" fill="{stroke}" '
            f'stroke="#ffffff" stroke-width="2" paint-order="stroke fill" '
            f'opacity="0.7" transform="{label_transform}">'
            f"{label_text}</text>"
        )
        lines.append("</g>")


def _expand_viewbox_for_wan(
    width: float,
    height: float,
    wan_info: WanInfo,
    node_types: dict[str, str],
    positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    options: SvgOptions,
) -> tuple[float, float]:
    """Expand viewBox dimensions to fit the WAN upstream box if needed."""
    gateway_name = next((name for name, ntype in node_types.items() if ntype == "gateway"), None)
    if not gateway_name or gateway_name not in positions:
        return width, height

    gx, gy = positions[gateway_name]
    label_lines = _build_wan_label_lines(wan_info)
    font_size = max(options.font_size - 1, 8)
    globe_size = 40
    padding = 12
    line_height = font_size + 4
    max_text_width = max((len(line) for line in label_lines), default=10) * font_size * 0.55
    box_width = max(globe_size + padding * 2, max_text_width + padding * 2)
    box_height = globe_size + len(label_lines) * line_height + padding * 3

    box_right = gx + layout.tile_width + 60 + box_width + padding
    box_top = gy - layout.tile_height / 2 - box_height / 2 + 38
    box_bottom = box_top + box_height + padding

    return max(width, box_right), max(height, box_bottom)


def _find_gateway_position(
    node_types: dict[str, str],
    positions: dict[str, tuple[float, float]],
) -> tuple[float, float] | None:
    for name, ntype in node_types.items():
        if ntype == "gateway" and name in positions:
            return positions[name]
    return None


def _maybe_render_wan_upstream(
    lines: list[str],
    wan_info: WanInfo | None,
    node_types: dict[str, str],
    positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    if not wan_info:
        return
    gateway_pos = _find_gateway_position(node_types, positions)
    if gateway_pos:
        _render_iso_wan_upstream(lines, wan_info, gateway_pos, layout, options, theme)


def _render_grouped_boundaries(
    lines: list[str],
    grid_positions: dict[str, tuple[float, float]],
    groups: dict[str, list[str]],
    group_order: list[str] | None,
    group_vlan_ids: dict[str, int] | None,
    layout: IsoLayout,
    layout_positions: IsoLayoutPositions,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    group_bounds_list = _compute_iso_group_bounds(
        grid_positions,
        groups,
        group_order,
        layout,
        layout_positions.offset_x,
        layout_positions.offset_y,
        options,
    )
    _render_iso_group_boundaries(lines, group_bounds_list, theme, group_vlan_ids=group_vlan_ids)


def _render_iso_grid(
    lines: list[str],
    grid_positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    theme: SvgTheme,
) -> None:
    grid_lines = _iso_grid_lines(grid_positions, layout, theme.grid_color)
    if grid_lines:
        lines.append('<g class="iso-grid" opacity="0.7">')
        lines.extend(grid_lines)
        lines.append("</g>")


def render_svg_isometric(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    group_vlan_ids: dict[str, int] | None = None,
    wan_info: WanInfo | None = None,
) -> str:
    """Render an isometric (2.5D) SVG network diagram.

    Same interface as :func:`~unifi_network_maps.render.render_svg` but produces
    a 30-degree isometric projection with 3D-style device tiles and grid floor.
    """
    options = options or SvgOptions()
    per_type_decals = _build_decal_colors(theme)
    icons = _load_isometric_icons(theme.icon_set, theme.icon_decal, per_type_decals)
    layout_positions = _iso_layout_positions(edges, node_types, options)
    layout = layout_positions.layout
    grid_positions = layout_positions.grid_positions
    positions = layout_positions.positions

    view_width = layout_positions.width
    view_height = layout_positions.height
    if wan_info:
        view_width, view_height = _expand_viewbox_for_wan(
            view_width, view_height, wan_info, node_types, positions, layout, options
        )

    out_width = options.width or int(view_width)
    out_height = options.height or int(view_height)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{out_width}" height="{out_height}" '
        f'viewBox="0 0 {view_width} {view_height}">',
        svg_defs("iso", theme),
        _svg_style_block(theme, options.font_size, iso=True),
        f'<rect width="100%" height="100%" fill="{theme.background}"/>',
    ]

    if options.layout_mode == "grouped" and groups:
        _render_grouped_boundaries(
            lines,
            grid_positions,
            groups,
            group_order,
            group_vlan_ids,
            layout,
            layout_positions,
            options,
            theme,
        )

    _render_iso_grid(lines, grid_positions, layout, theme)

    node_port_labels: dict[str, str] = {}
    node_port_prefix: dict[str, str] = {}
    _render_iso_edges(
        lines,
        edges,
        positions=positions,
        grid_positions=grid_positions,
        node_types=node_types,
        layout=layout,
        theme=theme,
        offset_x=layout_positions.offset_x,
        offset_y=layout_positions.offset_y,
        node_port_labels=node_port_labels,
        node_port_prefix=node_port_prefix,
    )
    _render_iso_nodes(
        lines,
        positions=positions,
        node_types=node_types,
        icons=icons,
        options=options,
        layout=layout,
        node_port_labels=node_port_labels,
        node_port_prefix=node_port_prefix,
        theme=theme,
    )

    _maybe_render_wan_upstream(lines, wan_info, node_types, positions, layout, options, theme)

    lines.append("</svg>")
    return "\n".join(lines) + "\n"
