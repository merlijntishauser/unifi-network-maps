"""SVG rendering for orthogonal network diagrams."""

from __future__ import annotations

import dataclasses

from ..model.topology import Edge, WanInfo
from .svg_edges import _render_svg_edges
from .svg_icons import (
    _TYPE_COLORS,
    _load_icons,
)
from .svg_labels import (
    _escape_text,
    _wrap_text,
)
from .svg_layout import (
    GroupBounds,
    _build_node_to_group_map,
    _layout_grouped_nodes,
    _layout_nodes,
    _svg_node_group_attrs,
)
from .svg_theme import DEFAULT_THEME, SvgOptions, SvgTheme, _svg_style_block, svg_defs
from .svg_wan import (
    _apply_wan_offset,
    _find_gateway_position,
    _render_group_boundaries,
    _render_wan_upstream,
)


def _compute_svg_layout(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]] | None,
    group_order: list[str] | None,
    wan_info: WanInfo | None,
) -> tuple[dict[str, tuple[float, float]], list[GroupBounds], float, float, bool]:
    """Compute node positions, group bounds, and canvas dimensions.

    Returns (positions, group_bounds_list, width, height, use_grouped).
    """
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

    return positions, group_bounds_list, float(width), float(height), bool(use_grouped)


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

    positions, group_bounds_list, width, height, use_grouped = _compute_svg_layout(
        edges, node_types, options, groups, group_order, wan_info
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


# --- Dual rendering ---


def _groups_from_vlan_node_map(
    vlan_node_map: dict[str, int | None],
    vlan_names: dict[int, str] | None = None,
) -> tuple[dict[str, list[str]], list[str], dict[str, int]]:
    """Convert a node-to-VLAN mapping into group structures.

    Returns (groups, group_order, group_vlan_ids) matching the format
    returned by group_nodes_by_vlan().
    """
    vlan_names = vlan_names or {}
    vlan_groups: dict[int, list[str]] = {}
    unassigned: list[str] = []

    for node in sorted(vlan_node_map):
        vlan_id = vlan_node_map[node]
        if vlan_id is None:
            unassigned.append(node)
        else:
            vlan_groups.setdefault(vlan_id, []).append(node)

    groups: dict[str, list[str]] = {}
    group_vlan_ids: dict[str, int] = {}
    group_order: list[str] = []

    for vlan_id in sorted(vlan_groups):
        name = vlan_names.get(vlan_id, f"VLAN {vlan_id}")
        groups[name] = vlan_groups[vlan_id]
        group_vlan_ids[name] = vlan_id
        group_order.append(name)

    if unassigned:
        groups["Unassigned"] = unassigned
        group_order.append("Unassigned")

    return groups, group_order, group_vlan_ids


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
    The "vlan" value is None when no VLAN data is available.
    """
    from ..model.edges import group_nodes_by_vlan

    options = options or SvgOptions()
    physical_options = dataclasses.replace(options, layout_mode="physical")

    if isometric:
        from .svg_isometric import render_svg_isometric

        render_fn = render_svg_isometric
    else:
        render_fn = render_svg

    physical_svg = render_fn(
        edges,
        node_types=node_types,
        options=physical_options,
        theme=theme,
        wan_info=wan_info,
    )

    # Build VLAN groups
    if vlan_node_map:
        groups, group_order, group_vlan_ids = _groups_from_vlan_node_map(vlan_node_map, vlan_names)
    elif vlan_names:
        groups, group_order, group_vlan_ids = group_nodes_by_vlan(edges, vlan_names)
    else:
        return {"physical": physical_svg, "vlan": None}

    if not groups:
        return {"physical": physical_svg, "vlan": None}

    grouped_options = dataclasses.replace(options, layout_mode="grouped")

    vlan_svg = render_fn(
        edges,
        node_types=node_types,
        options=grouped_options,
        theme=theme,
        groups=groups,
        group_order=group_order,
        group_vlan_ids=group_vlan_ids,
        wan_info=wan_info,
    )

    return {"physical": physical_svg, "vlan": vlan_svg}
