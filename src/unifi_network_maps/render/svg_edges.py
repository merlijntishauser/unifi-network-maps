"""Edge rendering for orthogonal SVG network diagrams."""

from __future__ import annotations

import math
from html import escape as _escape_html

from ..model.topology import Edge
from .svg_labels import (
    _compact_edge_label,
    _extract_device_name,
    _extract_port_text,
    _strip_local_port,
)
from .svg_theme import SvgOptions, SvgTheme


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


def _render_single_edge(
    lines: list[str],
    edge: Edge,
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    options: SvgOptions,
    theme: SvgTheme,
    max_vlan_colors: int | None,
) -> None:
    """Render a single edge with coordinates, attributes, and optional VLAN styling."""
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

    display_vlans = edge.active_vlans
    if max_vlan_colors and len(display_vlans) > max_vlan_colors:
        display_vlans = display_vlans[:max_vlan_colors]

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
        _render_single_edge(lines, edge, positions, node_types, options, theme, max_vlan_colors)
    return node_port_labels, node_port_prefix


def _record_client_label(
    raw_label: str,
    label_text: str,
    client_node: str,
    upstream_node: str,
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
) -> None:
    """Record port label for a client edge."""
    if "<->" in label_text:
        return
    upstream_part = raw_label.split("<->", 1)[0].strip()
    port_text = _extract_port_text(upstream_part) or label_text
    upstream_name = _extract_device_name(upstream_part) or upstream_node
    node_port_labels.setdefault(client_node, f"{upstream_name}: {port_text}")
    node_port_prefix.setdefault(client_node, upstream_name)


def _record_infra_label(
    edge: Edge,
    raw_label: str,
    label_text: str,
    right_type: str,
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
) -> None:
    """Record port label for an infrastructure edge."""
    upstream_part = raw_label.split("<->", 1)[0].strip()
    upstream_name = _extract_device_name(upstream_part) or edge.left
    if label_text.lower().startswith("port "):
        label_text = f"{upstream_name} {label_text}"
    label_text = _strip_local_port(label_text, right_type)
    node_port_labels.setdefault(edge.right, label_text)
    node_port_prefix.setdefault(edge.right, upstream_name)


def _record_edge_labels(
    edge: Edge,
    node_types: dict[str, str],
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
) -> None:
    if not edge.label:
        return
    raw_label = edge.label
    label_text = _compact_edge_label(raw_label, left_node=edge.left, right_node=edge.right)
    left_type = node_types.get(edge.left, "other")
    right_type = node_types.get(edge.right, "other")
    if left_type == "client" and right_type != "client":
        _record_client_label(
            raw_label, label_text, edge.left, edge.right, node_port_labels, node_port_prefix
        )
    elif right_type == "client" and left_type != "client":
        _record_client_label(
            raw_label, label_text, edge.right, edge.left, node_port_labels, node_port_prefix
        )
    else:
        _record_infra_label(
            edge, raw_label, label_text, right_type, node_port_labels, node_port_prefix
        )
