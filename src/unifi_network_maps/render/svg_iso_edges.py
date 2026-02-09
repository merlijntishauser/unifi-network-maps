"""Isometric edge rendering for SVG network diagrams."""

from __future__ import annotations

from html import escape as _escape_html

from ..model.topology import Edge
from .svg_edges import (
    _edge_opacity,
    _render_vlan_endpoint_markers,
    _vlan_data_attrs,
)
from .svg_iso_geometry import IsoLayout, _iso_project_center
from .svg_labels import (
    _compact_edge_label,
    _extract_device_name,
    _extract_port_text,
    _shorten_prefix,
    _strip_local_port,
)
from .svg_theme import SvgTheme


def _iso_front_anchor(
    layout: IsoLayout,
    *,
    gx: float,
    gy: float,
    offset_x: float,
    offset_y: float,
) -> tuple[float, float]:
    iso_x, iso_y = _iso_project_center(layout, gx, gy)
    cx = iso_x + offset_x + layout.tile_width / 2
    cy = iso_y + offset_y + layout.tile_height / 2
    return cx, cy


def _render_iso_vlan_striped_edge(
    lines: list[str],
    path: str,
    vlans: tuple[int, ...],
    theme: SvgTheme,
    base_width: int,
    is_wireless: bool,
    extra_attrs: str,
    opacity: float = 1.0,
) -> None:
    """Render an isometric edge with striped VLAN colors and glow effect."""
    if not vlans:
        return
    num_vlans = len(vlans)
    segment_len = 16  # Slightly larger for isometric view
    total_pattern = segment_len * num_vlans
    gap_len = total_pattern - segment_len
    opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

    # Render glow layer behind the edge
    glow_color = theme.vlan_color(vlans[0])
    glow_width = base_width * 3
    glow_opacity = 0.25 * opacity  # Scale glow with edge opacity
    lines.append(
        f'<path d="{path}" stroke="{glow_color}" stroke-width="{glow_width}" '
        f'fill="none" stroke-linecap="round" stroke-linejoin="round" '
        f'opacity="{glow_opacity}" filter="url(#iso-edge-glow)" {extra_attrs}/>'
    )

    for i, vlan_id in enumerate(vlans):
        color = theme.vlan_color(vlan_id)
        offset = -i * segment_len
        dash = f'stroke-dasharray="{segment_len} {gap_len}"'
        if is_wireless:
            dash = f'stroke-dasharray="6 3 6 {gap_len + 1}"'
        lines.append(
            f'<path d="{path}" stroke="{color}" stroke-width="{base_width}" '
            f'fill="none" stroke-linecap="round" stroke-linejoin="round" '
            f'{dash} stroke-dashoffset="{offset}"{opacity_attr} {extra_attrs}/>'
        )


def _render_iso_poe_icon(
    lines: list[str],
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    src_gx: float,
    src_gy: float,
    dst_gx: float,
    dst_gy: float,
    src_cx: float,
    src_cy: float,
    dst_cx: float,
    dst_cy: float,
    theme: SvgTheme,
    *,
    has_port_labels: bool = False,
) -> None:
    """Render PoE icon on an edge path."""
    poe_size = 30
    dx = dst_gx - src_gx
    dy = dst_gy - src_gy
    if dx == 0 or dy == 0:
        seg_start_x, seg_start_y = src_cx, src_cy
    else:
        elbow_cx, elbow_cy = _iso_front_anchor(
            layout, gx=dst_gx, gy=src_gy, offset_x=offset_x, offset_y=offset_y
        )
        seg_start_x, seg_start_y = elbow_cx, elbow_cy
    t = 0.15 if has_port_labels else 0.6
    icon_center_x = seg_start_x + t * (dst_cx - seg_start_x)
    icon_center_y = seg_start_y + t * (dst_cy - seg_start_y)
    icon_x = icon_center_x - poe_size / 2
    icon_y = icon_center_y - poe_size / 2
    lines.append(
        f'<use href="#iso-poe-bolt" x="{icon_x}" y="{icon_y}" '
        f'width="{poe_size}" height="{poe_size}" '
        f'fill="{theme.poe_fill}" stroke="{theme.poe_stroke}" stroke-width="1"/>'
    )


def _render_iso_standard_edge(
    lines: list[str],
    path: str,
    edge: Edge,
    width_px: int,
    base_attrs: str,
    opacity_attr: str,
) -> None:
    """Render a standard (non-VLAN) edge path."""
    color = "url(#iso-link-poe)" if edge.poe else "url(#iso-link-standard)"
    dash = ' stroke-dasharray="8 6"' if edge.wireless else ""
    lines.append(
        f'<path d="{path}" stroke="{color}" stroke-width="{width_px}" '
        f'fill="none" stroke-linecap="round" stroke-linejoin="round"{dash}{opacity_attr} '
        f"{base_attrs}/>"
    )


def _iso_edge_path(
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    src_gx: float,
    src_gy: float,
    dst_gx: float,
    dst_gy: float,
    src_cx: float,
    src_cy: float,
    dst_cx: float,
    dst_cy: float,
) -> list[str]:
    dx = dst_gx - src_gx
    dy = dst_gy - src_gy
    if dx == 0 or dy == 0:
        return [f"M {src_cx} {src_cy}", f"L {dst_cx} {dst_cy}"]
    elbow_gx, elbow_gy = dst_gx, src_gy
    elbow_cx, elbow_cy = _iso_front_anchor(
        layout,
        gx=elbow_gx,
        gy=elbow_gy,
        offset_x=offset_x,
        offset_y=offset_y,
    )
    return [
        f"M {src_cx} {src_cy}",
        f"L {elbow_cx} {elbow_cy}",
        f"L {dst_cx} {dst_cy}",
    ]


def _resolve_edge_coords(
    edge: Edge,
    grid_positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
) -> tuple[float, float, float, float, float, float, float, float] | None:
    src_grid = grid_positions.get(edge.left)
    dst_grid = grid_positions.get(edge.right)
    if not src_grid or not dst_grid:
        return None
    src_gx, src_gy = float(src_grid[0]), float(src_grid[1])
    dst_gx, dst_gy = float(dst_grid[0]), float(dst_grid[1])
    src_cx, src_cy = _iso_front_anchor(
        layout, gx=src_gx, gy=src_gy, offset_x=offset_x, offset_y=offset_y
    )
    dst_cx, dst_cy = _iso_front_anchor(
        layout, gx=dst_gx, gy=dst_gy, offset_x=offset_x, offset_y=offset_y
    )
    return src_gx, src_gy, dst_gx, dst_gy, src_cx, src_cy, dst_cx, dst_cy


def _render_single_iso_edge(
    lines: list[str],
    edge: Edge,
    coords: tuple[float, float, float, float, float, float, float, float],
    *,
    node_types: dict[str, str],
    layout: IsoLayout,
    theme: SvgTheme,
    offset_x: float,
    offset_y: float,
    node_port_labels: dict[str, str],
    max_vlan_colors: int | None,
) -> None:
    src_gx, src_gy, dst_gx, dst_gy, src_cx, src_cy, dst_cx, dst_cy = coords
    width_px = 5 if edge.poe else 4
    path_cmds = _iso_edge_path(
        layout,
        offset_x,
        offset_y,
        src_gx,
        src_gy,
        dst_gx,
        dst_gy,
        src_cx,
        src_cy,
        dst_cx,
        dst_cy,
    )
    path = " ".join(path_cmds)
    left_attr = _escape_html(edge.left, quote=True)
    right_attr = _escape_html(edge.right, quote=True)
    vlan_attrs = _vlan_data_attrs(edge)
    base_attrs = f'data-edge-left="{left_attr}" data-edge-right="{right_attr}"'
    if vlan_attrs:
        base_attrs = f"{base_attrs} {vlan_attrs}"

    display_vlans = edge.active_vlans
    if max_vlan_colors and len(display_vlans) > max_vlan_colors:
        display_vlans = display_vlans[:max_vlan_colors]

    opacity = _edge_opacity(node_types, edge)
    opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

    if display_vlans:
        _render_iso_vlan_striped_edge(
            lines, path, display_vlans, theme, width_px, edge.wireless, base_attrs, opacity
        )
        marker_x = dst_cx + layout.tile_width * 0.3
        marker_y = dst_cy - layout.tile_height * 0.2
        _render_vlan_endpoint_markers(lines, marker_x, marker_y, display_vlans, theme)
    else:
        _render_iso_standard_edge(lines, path, edge, width_px, base_attrs, opacity_attr)

    if edge.poe:
        dst_has_label = edge.right in node_port_labels
        _render_iso_poe_icon(
            lines,
            layout,
            offset_x,
            offset_y,
            src_gx,
            src_gy,
            dst_gx,
            dst_gy,
            src_cx,
            src_cy,
            dst_cx,
            dst_cy,
            theme,
            has_port_labels=dst_has_label,
        )


def _render_iso_edges(
    lines: list[str],
    edges: list[Edge],
    *,
    positions: dict[str, tuple[float, float]],
    grid_positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    layout: IsoLayout,
    theme: SvgTheme,
    offset_x: float,
    offset_y: float,
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
    max_vlan_colors: int | None = None,
) -> None:
    for edge in edges:
        _record_iso_edge_label(edge, node_types, node_port_labels, node_port_prefix)
    for edge in sorted(edges, key=lambda item: item.poe):
        if edge.left not in positions or edge.right not in positions:
            continue
        coords = _resolve_edge_coords(edge, grid_positions, layout, offset_x, offset_y)
        if not coords:
            continue
        _render_single_iso_edge(
            lines,
            edge,
            coords,
            node_types=node_types,
            layout=layout,
            theme=theme,
            offset_x=offset_x,
            offset_y=offset_y,
            node_port_labels=node_port_labels,
            max_vlan_colors=max_vlan_colors,
        )


def _record_iso_edge_label(
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
            node_port_labels.setdefault(client_node, f"{upstream_node}: {port_text}")
            node_port_prefix.setdefault(client_node, _shorten_prefix(upstream_node))
        return
    upstream_part = edge.label.split("<->", 1)[0].strip()
    upstream_name = _extract_device_name(upstream_part) or edge.left
    if label_text.lower().startswith("port "):
        label_text = f"{upstream_name} {label_text}"
    label_text = _strip_local_port(label_text, right_type)
    node_port_labels.setdefault(edge.right, label_text)
    node_port_prefix.setdefault(edge.right, _shorten_prefix(edge.left))
