"""WAN upstream and group boundary rendering for SVG diagrams."""

from __future__ import annotations

from html import escape as _escape_html

from ..model.topology import WanInfo
from .svg_labels import _build_wan_label_lines, _escape_text
from .svg_layout import GroupBounds
from .svg_theme import SvgOptions, SvgTheme


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
