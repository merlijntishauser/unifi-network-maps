"""SVG rendering for orthogonal network diagrams."""

from __future__ import annotations

import base64
import dataclasses
import functools
from dataclasses import dataclass
from html import escape as _escape_html
from pathlib import Path

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
    _layout_grouped_nodes,
    _layout_nodes,
)
from .svg_theme import DEFAULT_THEME, SvgTheme, svg_defs
from .svg_wan import (
    _apply_wan_offset,
    _find_gateway_position,
    _render_group_boundaries,
    _render_wan_upstream,
)

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
