"""SVG rendering for orthogonal network diagrams."""

from __future__ import annotations

import base64
import functools
import math
from collections.abc import Callable
from dataclasses import dataclass
from html import escape as _escape_html
from pathlib import Path

from ..model.topology import Edge, WanInfo
from .svg_icons import (
    _TYPE_COLORS,
    _TYPE_ORDER,
    _load_icons,
)
from .svg_labels import (
    _build_wan_label_lines,
    _compact_edge_label,
    _escape_text,
    _extract_device_name,
    _extract_port_text,
    _strip_local_port,
    _wrap_text,
)
from .svg_theme import DEFAULT_THEME, SvgTheme, svg_defs

_FONTS_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
_SYSTEM_FONT_STACK = "Arial,Helvetica,sans-serif"


@functools.lru_cache(maxsize=4)
def _build_font_style(font_family: str | None) -> tuple[str, str]:
    """Build @font-face CSS and font-family stack for the given font.

    Results are cached to avoid repeated disk I/O for the same font family.
    Returns (font_face_css, font_family_css) where font_face_css may be empty.
    """
    if not font_family:
        return "", _SYSTEM_FONT_STACK

    slug = font_family.lower().replace(" ", "-")
    font_face_parts: list[str] = []

    for weight, suffix in ((400, "regular"), (600, "semibold")):
        path = _FONTS_DIR / f"{slug}-{suffix}.woff2"
        if not path.exists():
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        font_face_parts.append(
            f"@font-face{{font-family:'{font_family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )

    if not font_face_parts:
        return "", _SYSTEM_FONT_STACK

    font_face_css = "".join(font_face_parts)
    family_css = f"'{font_family}',{_SYSTEM_FONT_STACK}"
    return font_face_css, family_css


def _svg_style_block(theme: SvgTheme, font_size: int, *, iso: bool = False) -> str:
    """Build the <style> element for an SVG, including optional @font-face."""
    font_face, family = _build_font_style(theme.font_family)
    parts = [f"<style>{font_face}"]

    if iso:
        parts.append(f"text{{font-family:{family};}}")
        parts.append(f"text:not(.group-label){{font-size:{font_size}px;}}")
    else:
        parts.append(f"text{{font-family:{family};font-size:{font_size}px;}}")

    parts.append("text.node-label{font-weight:600;}")
    parts.append("</style>")
    return "".join(parts)


@dataclass(frozen=True)
class SvgOptions:
    node_width: int = 160
    node_height: int = 48
    h_gap: int = 80
    v_gap: int = 80
    padding: int = 40
    font_size: int = 10
    icon_size: int = 18
    width: int | None = None
    height: int | None = None
    layout_mode: str = "physical"  # "physical" | "grouped"
    group_padding: int = 20
    group_gap: int = 40


def _layout_nodes(
    edges: list[Edge], node_types: dict[str, str], options: SvgOptions
) -> tuple[dict[str, tuple[float, float]], int, int]:
    positions_index, levels = _tree_layout_indices(edges, node_types)
    positions: dict[str, tuple[float, float]] = {}
    max_index = max(positions_index.values(), default=0.0)
    leaf_count = max(1, math.ceil(max_index) + 1)
    for name, idx in positions_index.items():
        level = levels.get(name, 0)
        x = options.padding + idx * (options.node_width + options.h_gap)
        y = options.padding + level * (options.node_height + options.v_gap)
        positions[name] = (x, y)

    width = (
        options.padding * 2
        + leaf_count * options.node_width
        + max(0, leaf_count - 1) * options.h_gap
    )
    max_level = max(levels.values(), default=0)
    height = (
        options.padding * 2
        + (max_level + 1) * options.node_height
        + max(0, max_level) * options.v_gap
    )
    return positions, width, height


def _layout_nodeset(edges: list[Edge], node_types: dict[str, str]) -> set[str]:
    nodes = set(node_types.keys())
    for edge in edges:
        nodes.add(edge.left)
        nodes.add(edge.right)
    return nodes


def _build_children_maps(
    edges: list[Edge], nodes: set[str]
) -> tuple[dict[str, list[str]], dict[str, int]]:
    children: dict[str, list[str]] = {name: [] for name in nodes}
    incoming: dict[str, int] = {name: 0 for name in nodes}
    for edge in edges:
        children[edge.left].append(edge.right)
        incoming[edge.right] = incoming.get(edge.right, 0) + 1
    return children, incoming


def _sort_key_for_nodes(node_types: dict[str, str]) -> Callable[[str], tuple[int, str]]:
    type_order = {t: i for i, t in enumerate(_TYPE_ORDER)}

    def sort_key(name: str) -> tuple[int, str]:
        return (type_order.get(node_types.get(name, "other"), 99), name.lower())

    return sort_key


def _sort_children(children: dict[str, list[str]], sort_key) -> None:
    for _parent, child_list in children.items():
        child_list.sort(key=sort_key)


def _resolve_roots(
    nodes: set[str],
    incoming: dict[str, int],
    node_types: dict[str, str],
    sort_key,
) -> list[str]:
    gateways = [n for n, t in node_types.items() if t == "gateway"]
    roots = gateways if gateways else [n for n in nodes if incoming.get(n, 0) == 0]
    if not roots:
        roots = list(nodes)
    return sorted(roots, key=sort_key)


def _layout_positions(
    nodes: set[str],
    children: dict[str, list[str]],
    *,
    roots: list[str],
    sort_key,
) -> tuple[dict[str, float], dict[str, int]]:
    levels: dict[str, int] = {}
    positions_index: dict[str, float] = {}
    visited: set[str] = set()
    cursor = 0

    def dfs(node: str, level: int) -> float:
        nonlocal cursor
        if node in positions_index:
            return positions_index[node]
        visited.add(node)
        levels[node] = min(levels.get(node, level), level)
        child_list = children.get(node, [])
        if not child_list:
            idx = float(cursor)
            cursor += 1
            positions_index[node] = idx
            return idx
        child_indices: list[float] = []
        for child in child_list:
            if child in visited:
                child_indices.append(positions_index.get(child, float(cursor)))
                continue
            child_indices.append(dfs(child, level + 1))
        if not child_indices:
            idx = float(cursor)
            cursor += 1
            positions_index[node] = idx
            return idx
        idx = sum(child_indices) / len(child_indices)
        positions_index[node] = idx
        return idx

    for root in roots:
        dfs(root, 0)
    for node in sorted(nodes, key=sort_key):
        if node not in positions_index:
            dfs(node, 0)
    return positions_index, levels


def _tree_layout_indices(
    edges: list[Edge], node_types: dict[str, str]
) -> tuple[dict[str, float], dict[str, int]]:
    nodes = _layout_nodeset(edges, node_types)
    children, incoming = _build_children_maps(edges, nodes)
    sort_key = _sort_key_for_nodes(node_types)
    _sort_children(children, sort_key)
    roots = _resolve_roots(nodes, incoming, node_types, sort_key)
    return _layout_positions(nodes, children, roots=roots, sort_key=sort_key)


# --- Grouped layout functions ---


@dataclass(frozen=True)
class GroupBounds:
    name: str
    x: float
    y: float
    width: float
    height: float


def _assign_nodes_to_groups(
    nodes: set[str],
    groups: dict[str, list[str]],
) -> dict[str, str]:
    """Map each node to its group name."""
    node_to_group: dict[str, str] = {}
    for group_name, members in groups.items():
        for node in members:
            if node in nodes:
                node_to_group[node] = group_name
    return node_to_group


def _resolve_group_order(
    groups: dict[str, list[str]],
    group_order: list[str] | None,
) -> list[str]:
    """Return ordered list of group names."""
    if group_order:
        return [g for g in group_order if g in groups]
    return sorted(groups.keys())


def _filter_edges_for_group(
    edges: list[Edge],
    group_nodes: set[str],
) -> list[Edge]:
    """Return edges where both endpoints are in the group."""
    return [e for e in edges if e.left in group_nodes and e.right in group_nodes]


def _layout_single_group(
    edges: list[Edge],
    group_nodes: set[str],
    node_types: dict[str, str],
    options: SvgOptions,
) -> tuple[dict[str, tuple[float, float]], float, float]:
    """Layout nodes within a single group, return positions and dimensions."""
    group_edges = _filter_edges_for_group(edges, group_nodes)
    group_node_types = {n: node_types.get(n, "other") for n in group_nodes}
    positions, width, height = _layout_nodes(group_edges, group_node_types, options)
    return positions, float(width), float(height)


def _compute_group_bounds(
    group_name: str,
    positions: dict[str, tuple[float, float]],
    options: SvgOptions,
    offset_x: float,
) -> GroupBounds:
    """Compute bounding rectangle for a group."""
    if not positions:
        return GroupBounds(group_name, offset_x, 0, 100, 100)
    xs = [x for x, _ in positions.values()]
    ys = [y for _, y in positions.values()]
    min_x = min(xs) - options.group_padding
    min_y = min(ys) - options.group_padding
    max_x = max(xs) + options.node_width + options.group_padding
    max_y = max(ys) + options.node_height + options.group_padding
    return GroupBounds(group_name, min_x, min_y, max_x - min_x, max_y - min_y)


def _offset_positions(
    positions: dict[str, tuple[float, float]],
    dx: float,
    dy: float,
) -> dict[str, tuple[float, float]]:
    """Shift all positions by (dx, dy)."""
    return {name: (x + dx, y + dy) for name, (x, y) in positions.items()}


def _layout_grouped_nodes(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]],
    group_order: list[str] | None,
) -> tuple[dict[str, tuple[float, float]], list[GroupBounds], int, int]:
    """Layout nodes in horizontal group lanes."""
    all_nodes = _layout_nodeset(edges, node_types)
    ordered_groups = _resolve_group_order(groups, group_order)
    node_to_group = _assign_nodes_to_groups(all_nodes, groups)

    all_positions: dict[str, tuple[float, float]] = {}
    group_bounds_list: list[GroupBounds] = []
    current_x = float(options.padding)
    max_height = 0.0

    for group_name in ordered_groups:
        group_nodes = set(groups.get(group_name, []))
        group_nodes = group_nodes & all_nodes
        if not group_nodes:
            continue
        positions, width, height = _layout_single_group(edges, group_nodes, node_types, options)
        offset_x = current_x - options.padding
        offset_positions = _offset_positions(positions, offset_x, 0)
        all_positions.update(offset_positions)
        bounds = _compute_group_bounds(group_name, offset_positions, options, current_x)
        group_bounds_list.append(bounds)
        current_x += width + options.group_gap
        max_height = max(max_height, height)

    ungrouped = all_nodes - set(node_to_group.keys())
    if ungrouped:
        ungrouped_positions, ug_width, ug_height = _layout_single_group(
            edges, ungrouped, node_types, options
        )
        offset_positions = _offset_positions(ungrouped_positions, current_x - options.padding, 0)
        all_positions.update(offset_positions)
        bounds = _compute_group_bounds("Other", offset_positions, options, current_x)
        group_bounds_list.append(bounds)
        current_x += ug_width + options.group_gap
        max_height = max(max_height, ug_height)

    total_width = int(current_x - options.group_gap + options.padding)
    total_height = int(max_height)
    return all_positions, group_bounds_list, total_width, total_height


def _vlan_group_colors(
    group_name: str,
    theme: SvgTheme,
    group_vlan_ids: dict[str, int] | None,
) -> tuple[str, str]:
    """Return (fill, stroke) for a group, using VLAN color when available."""
    if group_vlan_ids and group_name in group_vlan_ids:
        color = theme.vlan_color(group_vlan_ids[group_name])
        return color, color
    return theme.group_colors(group_name)


def _render_group_boundaries(
    lines: list[str],
    group_bounds_list: list[GroupBounds],
    theme: SvgTheme,
    options: SvgOptions,
    *,
    group_vlan_ids: dict[str, int] | None = None,
) -> None:
    """Render group background rectangles and labels."""
    label_size = options.font_size + 4
    for bounds in group_bounds_list:
        group_attr = _escape_html(bounds.name, quote=True)
        fill, stroke = _vlan_group_colors(bounds.name, theme, group_vlan_ids)
        lines.append(f'<g class="network-group" data-group-name="{group_attr}">')
        lines.append(
            f'<rect class="group-boundary" x="{bounds.x}" y="{bounds.y}" '
            f'width="{bounds.width}" height="{bounds.height}" '
            f'rx="{theme.group_radius}" fill="{fill}" fill-opacity="0.3" '
            f'stroke="{stroke}" stroke-width="{theme.group_stroke_width}"/>'
        )
        label_x = bounds.x + 10
        label_y = bounds.y + label_size + 2
        lines.append(
            f'<text class="group-label" x="{label_x}" y="{label_y}" '
            f'fill="{stroke}" font-size="{label_size}" font-weight="bold">'
            f"{_escape_text(bounds.name.capitalize())}</text>"
        )
        lines.append("</g>")


def _wan_box_dimensions(
    label_lines: list[str],
    font_size: int,
) -> tuple[int, int, int, float, float]:
    """Calculate WAN box dimensions from label content."""
    globe_size = 36
    padding = 10
    line_height = font_size + 4
    max_text_width = max((len(line) for line in label_lines), default=10) * font_size * 0.55
    box_width = max(globe_size + padding * 2, max_text_width + padding * 2)
    box_height = globe_size + len(label_lines) * line_height + padding * 3
    return globe_size, padding, line_height, box_width, box_height


def _render_wan_globe(
    lines: list[str],
    globe_cx: float,
    globe_cy: float,
    globe_r: float,
) -> None:
    """Render the WAN globe icon with gradient fill."""
    lines.append(f'<g transform="translate({globe_cx}, {globe_cy})">')
    lines.append(
        f'<circle cx="0" cy="0" r="{globe_r}" fill="none" stroke="url(#globe)" stroke-width="1.5"/>'
    )
    lines.append(
        f'<ellipse cx="0" cy="0" rx="{globe_r * 0.35}" ry="{globe_r}" '
        f'fill="none" stroke="url(#globe)" stroke-width="1.2"/>'
    )
    lines.append(
        f'<line x1="{-globe_r}" y1="0" x2="{globe_r}" y2="0" '
        f'stroke="url(#globe)" stroke-width="1.2"/>'
    )
    lines.append(
        f'<ellipse cx="0" cy="{-globe_r * 0.5}" rx="{globe_r * 0.87}" ry="{globe_r * 0.18}" '
        f'fill="none" stroke="url(#globe)" stroke-width="0.8"/>'
    )
    lines.append(
        f'<ellipse cx="0" cy="{globe_r * 0.5}" rx="{globe_r * 0.87}" ry="{globe_r * 0.18}" '
        f'fill="none" stroke="url(#globe)" stroke-width="0.8"/>'
    )
    lines.append("</g>")


def _render_wan_labels(
    lines: list[str],
    label_lines: list[str],
    text_x: float,
    text_y: float,
    line_height: int,
    font_size: int,
    theme: SvgTheme,
) -> None:
    """Render WAN status text labels."""
    for i, label_text in enumerate(label_lines):
        y = text_y + i * line_height
        lines.append(
            f'<text x="{text_x}" y="{y}" text-anchor="middle" '
            f'fill="{theme.text_primary}" font-size="{font_size}">'
            f"{_escape_text(label_text)}</text>"
        )


def _render_wan_upstream(
    lines: list[str],
    wan_info: WanInfo,
    gateway_position: tuple[float, float],
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    """Render WAN upstream visualization (orthogonal view)."""
    gx, gy = gateway_position
    font_size = options.font_size
    label_lines = _build_wan_label_lines(wan_info)
    globe_size, padding, line_height, box_width, box_height = _wan_box_dimensions(
        label_lines, font_size
    )

    # Position box above the gateway
    box_x = gx + options.node_width / 2 - box_width / 2
    box_y = gy - box_height - 30

    # Connection points
    gw_cx = gx + options.node_width / 2
    gw_cy = gy
    box_cx = box_x + box_width / 2
    box_cy = box_y + box_height

    lines.append('<g class="wan-upstream">')
    lines.append(
        f'<path d="M {gw_cx} {gw_cy} L {box_cx} {box_cy}" '
        f'stroke="#0288d1" stroke-width="2" fill="none" '
        f'stroke-linecap="round" opacity="0.8"/>'
    )
    lines.append(
        f'<rect x="{box_x}" y="{box_y}" width="{box_width}" height="{box_height}" '
        f'rx="6" ry="6" fill="{theme.wan_background}" stroke="{theme.wan_globe[1]}" stroke-width="1.5"/>'
    )

    globe_cx = box_x + box_width / 2
    globe_cy = box_y + padding + globe_size / 2
    globe_r = globe_size / 2 - 2
    _render_wan_globe(lines, globe_cx, globe_cy, globe_r)

    text_x = box_x + box_width / 2
    text_y = box_y + padding + globe_size + padding + font_size
    _render_wan_labels(lines, label_lines, text_x, text_y, line_height, font_size, theme)

    lines.append("</g>")


def _apply_wan_offset(
    positions: dict[str, tuple[float, float]],
    group_bounds_list: list[GroupBounds],
    height: float,
    wan_offset_y: float,
) -> tuple[dict[str, tuple[float, float]], list[GroupBounds], float]:
    """Shift positions and group bounds down to make room for WAN box."""
    shifted_positions = {name: (x, y + wan_offset_y) for name, (x, y) in positions.items()}
    shifted_bounds = [
        GroupBounds(
            name=gb.name,
            x=gb.x,
            y=gb.y + wan_offset_y,
            width=gb.width,
            height=gb.height,
        )
        for gb in group_bounds_list
    ]
    return shifted_positions, shifted_bounds, height + wan_offset_y


def _find_gateway_position(
    node_types: dict[str, str],
    positions: dict[str, tuple[float, float]],
) -> tuple[float, float] | None:
    """Find the position of the gateway node."""
    for name, ntype in node_types.items():
        if ntype == "gateway" and name in positions:
            return positions[name]
    return None


def render_svg(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    node_data: dict[str, dict[str, str]] | None = None,
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    group_vlan_ids: dict[str, int] | None = None,
    wan_info: WanInfo | None = None,
) -> str:
    options = options or SvgOptions()
    icons = _load_icons(theme.icon_set, decal_color=theme.text_primary)

    use_grouped = options.layout_mode == "grouped" and groups
    group_bounds_list: list[GroupBounds] = []
    if use_grouped and groups:
        positions, group_bounds_list, width, height = _layout_grouped_nodes(
            edges, node_types, options, groups, group_order
        )
    else:
        positions, width, height = _layout_nodes(edges, node_types, options)

    if wan_info:
        wan_box_height = 36 + 3 * (options.font_size + 4) + 30 + 30
        positions, group_bounds_list, height = _apply_wan_offset(
            positions, group_bounds_list, height, wan_box_height
        )

    out_width = options.width or width
    out_height = options.height or height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{out_width}" height="{out_height}" '
        f'viewBox="0 0 {width} {height}">',
        svg_defs("", theme),
        _svg_style_block(theme, options.font_size),
        f'<rect width="100%" height="100%" fill="{theme.background}"/>',
    ]

    if use_grouped and group_bounds_list:
        _render_group_boundaries(
            lines, group_bounds_list, theme, options, group_vlan_ids=group_vlan_ids
        )

    node_port_labels, _ = _render_svg_edges(lines, edges, positions, node_types, options, theme)
    _render_svg_nodes(
        lines,
        positions,
        node_types,
        node_port_labels,
        icons,
        options,
        node_data,
        theme,
        groups=groups,
    )

    if wan_info:
        gateway_pos = _find_gateway_position(node_types, positions)
        if gateway_pos:
            _render_wan_upstream(lines, wan_info, gateway_pos, options, theme)

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _vlan_data_attrs(edge: Edge) -> str:
    """Generate VLAN data attributes for an edge."""
    attrs = []
    if edge.vlans:
        attrs.append(f'data-vlans="{",".join(str(v) for v in edge.vlans)}"')
    if edge.active_vlans:
        attrs.append(f'data-active-vlans="{",".join(str(v) for v in edge.active_vlans)}"')
    if edge.is_trunk:
        attrs.append('data-trunk="true"')
    return " ".join(attrs)


def _edge_opacity(node_types: dict[str, str], edge: Edge) -> float:
    """Return opacity for edge based on endpoint types.

    Client edges are semi-transparent to reduce visual clutter
    and keep focus on infrastructure connections.
    """
    left_type = node_types.get(edge.left, "other")
    right_type = node_types.get(edge.right, "other")

    if right_type == "client" or left_type == "client":
        return 0.5

    return 1.0


def _render_vlan_endpoint_markers(
    lines: list[str],
    x: float,
    y: float,
    vlans: tuple[int, ...],
    theme: SvgTheme,
    marker_size: int = 6,
    max_markers: int = 4,
) -> None:
    """Render small colored squares showing active VLANs at an endpoint."""
    if not vlans:
        return
    for i, vlan_id in enumerate(vlans[:max_markers]):
        color = theme.vlan_color(vlan_id)
        marker_x = x - marker_size - 2
        marker_y = y + (i * (marker_size + 2))
        lines.append(
            f'<rect x="{marker_x}" y="{marker_y}" width="{marker_size}" '
            f'height="{marker_size}" fill="{color}" stroke="#fff" '
            f'stroke-width="0.5" rx="1" data-vlan="{vlan_id}">'
            f"<title>VLAN {vlan_id}</title></rect>"
        )


def _render_vlan_striped_edge(
    lines: list[str],
    path: str,
    vlans: tuple[int, ...],
    theme: SvgTheme,
    base_width: int,
    is_wireless: bool,
    extra_attrs: str,
    opacity: float = 1.0,
) -> None:
    """Render an edge with striped VLAN colors and glow effect."""
    if not vlans:
        return
    num_vlans = len(vlans)
    segment_len = 12  # Length of each colored segment
    total_pattern = segment_len * num_vlans
    gap_len = total_pattern - segment_len  # Gap is rest of pattern
    opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

    # Render glow layer behind the edge
    glow_color = theme.vlan_color(vlans[0])
    glow_width = base_width * 3
    glow_opacity = 0.25 * opacity  # Scale glow with edge opacity
    lines.append(
        f'<path d="{path}" stroke="{glow_color}" stroke-width="{glow_width}" '
        f'fill="none" opacity="{glow_opacity}" filter="url(#edge-glow)" {extra_attrs}/>'
    )

    for i, vlan_id in enumerate(vlans):
        color = theme.vlan_color(vlan_id)
        offset = -i * segment_len
        dash = f'stroke-dasharray="{segment_len} {gap_len}"'
        if is_wireless:
            # For wireless, use smaller dashes within the segment
            dash = f'stroke-dasharray="4 2 4 {gap_len + 2}"'
        lines.append(
            f'<path d="{path}" stroke="{color}" stroke-width="{base_width}" '
            f'fill="none" {dash} stroke-dashoffset="{offset}"{opacity_attr} {extra_attrs}/>'
        )


def _compute_elbow_path(
    src_cx: float, src_bottom: float, dst_cx: float, dst_top: float, mid_y: float
) -> str:
    """Compute SVG path for an elbow connector between two nodes."""
    if math.isclose(src_cx, dst_cx, abs_tol=0.01):
        elbow_x = src_cx + 0.5
        return (
            f"M {src_cx} {src_bottom} L {src_cx} {mid_y} "
            f"L {elbow_x} {mid_y} L {dst_cx} {mid_y} L {dst_cx} {dst_top}"
        )
    return f"M {src_cx} {src_bottom} L {src_cx} {mid_y} L {dst_cx} {mid_y} L {dst_cx} {dst_top}"


def _render_poe_icon(
    lines: list[str], dst_cx: float, mid_y: float, dst_top: float, theme: SvgTheme
) -> None:
    """Render PoE lightning bolt icon on an edge."""
    poe_size = 16
    icon_x = dst_cx - poe_size / 2
    icon_center_y = mid_y + 0.8 * (dst_top - mid_y)
    icon_y = icon_center_y - poe_size / 2
    lines.append(
        f'<use href="#poe-bolt" x="{icon_x}" y="{icon_y}" '
        f'width="{poe_size}" height="{poe_size}" '
        f'fill="{theme.poe_fill}" stroke="{theme.poe_stroke}" stroke-width="0.5"/>'
    )


def _render_standard_edge(
    lines: list[str],
    path: str,
    edge: Edge,
    opacity_attr: str,
    base_attrs: str,
) -> None:
    """Render a standard edge (no VLAN coloring)."""
    color = "url(#link-poe)" if edge.poe else "url(#link-standard)"
    dash = ' stroke-dasharray="6 4"' if edge.wireless else ""
    width_px = 2 if edge.poe else 1
    lines.append(
        f'<path d="{path}" stroke="{color}" stroke-width="{width_px}" '
        f'fill="none"{dash}{opacity_attr} {base_attrs}/>'
    )


def _render_svg_edges(
    lines: list[str],
    edges: list[Edge],
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    options: SvgOptions,
    theme: SvgTheme,
    max_vlan_colors: int | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    node_port_labels: dict[str, str] = {}
    node_port_prefix: dict[str, str] = {}
    for edge in edges:
        _record_edge_labels(edge, node_types, node_port_labels, node_port_prefix)
    for edge in sorted(edges, key=lambda item: item.poe):
        if edge.left not in positions or edge.right not in positions:
            continue
        src_x, src_y = positions[edge.left]
        dst_x, dst_y = positions[edge.right]
        src_cx = src_x + options.node_width / 2
        dst_cx = dst_x + options.node_width / 2
        src_bottom = src_y + options.node_height
        dst_top = dst_y
        mid_y = (src_bottom + dst_top) / 2
        width_px = 2 if edge.poe else 1

        path = _compute_elbow_path(src_cx, src_bottom, dst_cx, dst_top, mid_y)
        left_attr = _escape_html(edge.left, quote=True)
        right_attr = _escape_html(edge.right, quote=True)
        vlan_attrs = _vlan_data_attrs(edge)
        base_attrs = f'data-edge-left="{left_attr}" data-edge-right="{right_attr}"'
        if vlan_attrs:
            base_attrs = f"{base_attrs} {vlan_attrs}"

        # Determine VLANs to visualize (active only, with optional limit)
        display_vlans = edge.active_vlans
        if max_vlan_colors and len(display_vlans) > max_vlan_colors:
            display_vlans = display_vlans[:max_vlan_colors]

        # Client edges are semi-transparent to reduce visual clutter
        opacity = _edge_opacity(node_types, edge)
        opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

        if display_vlans:
            _render_vlan_striped_edge(
                lines, path, display_vlans, theme, width_px, edge.wireless, base_attrs, opacity
            )
            _render_vlan_endpoint_markers(lines, dst_cx, dst_top + 4, display_vlans, theme)
        else:
            _render_standard_edge(lines, path, edge, opacity_attr, base_attrs)

        if edge.poe:
            _render_poe_icon(lines, dst_cx, mid_y, dst_top, theme)
    return node_port_labels, node_port_prefix


def _record_edge_labels(
    edge: Edge,
    node_types: dict[str, str],
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
) -> None:
    if not edge.label:
        return
    label_text = _compact_edge_label(edge.label, left_node=edge.left, right_node=edge.right)
    left_type = node_types.get(edge.left, "other")
    right_type = node_types.get(edge.right, "other")
    client_node = None
    upstream_node = None
    if left_type == "client" and right_type != "client":
        client_node = edge.left
        upstream_node = edge.right
    elif right_type == "client" and left_type != "client":
        client_node = edge.right
        upstream_node = edge.left
    if client_node and upstream_node:
        if "<->" not in label_text:
            upstream_part = edge.label.split("<->", 1)[0].strip()
            port_text = _extract_port_text(upstream_part) or label_text
            upstream_name = _extract_device_name(upstream_part) or upstream_node
            node_port_labels.setdefault(client_node, f"{upstream_name}: {port_text}")
            node_port_prefix.setdefault(client_node, upstream_name)
        return
    upstream_part = edge.label.split("<->", 1)[0].strip()
    upstream_name = _extract_device_name(upstream_part) or edge.left
    if label_text.lower().startswith("port "):
        label_text = f"{upstream_name} {label_text}"
    label_text = _strip_local_port(label_text, right_type)
    node_port_labels.setdefault(edge.right, label_text)
    node_port_prefix.setdefault(edge.right, upstream_name)


def _render_svg_nodes(
    lines: list[str],
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    node_port_labels: dict[str, str],
    icons: dict[str, str],
    options: SvgOptions,
    node_data: dict[str, dict[str, str]] | None,
    theme: SvgTheme,
    *,
    groups: dict[str, list[str]] | None = None,
) -> None:
    node_to_group = _build_node_to_group_map(groups) if groups else {}
    for name, (x, y) in positions.items():
        node_type = node_types.get(name, "other")
        fill, stroke = _TYPE_COLORS.get(node_type, _TYPE_COLORS["other"])
        fill = f"url(#node-{node_type})"
        group_name = node_to_group.get(name)
        group_attrs = _svg_node_group_attrs(node_data, name, node_type, group_name)
        lines.append(f"<g{group_attrs}>")
        lines.append(f"<title>{_escape_text(name)}</title>")
        lines.append(
            f'<rect x="{x}" y="{y}" width="{options.node_width}" height="{options.node_height}" '
            'fill="transparent" pointer-events="all" class="node-hitbox"/>'
        )
        lines.append(
            f'<rect x="{x}" y="{y}" width="{options.node_width}" height="{options.node_height}" '
            f'rx="6" ry="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        icon_href = icons.get(node_type, icons.get("other"))
        if icon_href:
            icon_x = x + 8
            icon_y = y + (options.node_height - options.icon_size) / 2
            lines.append(
                f'<image href="{icon_href}" x="{icon_x}" y="{icon_y}" '
                f'width="{options.icon_size}" height="{options.icon_size}"/>'
            )
            text_x = icon_x + options.icon_size + 6
        else:
            text_x = x + 10
        port_label = node_port_labels.get(name)
        if port_label:
            text_y = y + options.node_height - 6
        else:
            text_y = y + options.node_height / 2 + options.font_size / 2 - 2
        safe_name = _escape_text(name)
        if port_label:
            font_size = max(options.font_size - 2, 8)
            line_height = font_size + 2
            port_y = y + font_size + 4
            wrapped = _wrap_text(port_label)
            lines.append(
                f'<text x="{text_x}" y="{port_y}" class="node-port" '
                f'text-anchor="start" fill="{theme.text_secondary}" font-size="{font_size}">'
            )
            for idx, line in enumerate(wrapped):
                dy = 0 if idx == 0 else line_height
                lines.append(f'<tspan x="{text_x}" dy="{dy}">{_escape_text(line)}</tspan>')
            lines.append("</text>")
        lines.append(
            f'<text x="{text_x}" y="{text_y}" class="node-label" fill="{theme.text_primary}" '
            f'text-anchor="start">{safe_name}</text>'
        )
        lines.append("</g>")


def _build_node_to_group_map(groups: dict[str, list[str]]) -> dict[str, str]:
    """Build reverse mapping from node to group name."""
    result: dict[str, str] = {}
    for group_name, members in groups.items():
        for node in members:
            result[node] = group_name
    return result


def _svg_node_group_attrs(
    node_data: dict[str, dict[str, str]] | None,
    name: str,
    node_type: str,
    group_name: str | None = None,
) -> str:
    attrs: dict[str, str] = {
        "class": "unm-node",
        "data-node-id": name,
        "data-node-type": node_type,
    }
    if group_name:
        attrs["data-group"] = group_name
    if node_data and (extra := node_data.get(name)):
        for key, value in extra.items():
            if key == "class":
                attrs["class"] = f"{attrs['class']} {value}".strip()
            else:
                attrs[key] = value
    rendered = [f' {key}="{_escape_html(value, quote=True)}"' for key, value in attrs.items()]
    return "".join(rendered)
