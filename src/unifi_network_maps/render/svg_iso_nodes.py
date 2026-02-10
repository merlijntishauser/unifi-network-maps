"""Isometric node rendering for SVG network diagrams."""

from __future__ import annotations

import math

from .svg_icons import _TYPE_COLORS
from .svg_iso_geometry import (
    IsoLayout,
    _iso_front_text_position,
    _iso_name_label_position,
    _iso_tile_points,
    _points_to_svg,
    _render_iso_text,
)
from .svg_labels import (
    _escape_text,
    _format_port_label_lines,
)
from .svg_layout import _svg_node_group_attrs
from .svg_theme import SvgOptions, SvgTheme


def _iso_node_polygons(
    x: float,
    y: float,
    tile_w: float,
    tile_h: float,
    node_depth: float,
) -> tuple[list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]]]:
    top = [
        (x + tile_w / 2, y),
        (x + tile_w, y + tile_h / 2),
        (x + tile_w / 2, y + tile_h),
        (x, y + tile_h / 2),
    ]
    left = [
        (x, y + tile_h / 2),
        (x + tile_w / 2, y + tile_h),
        (x + tile_w / 2, y + tile_h + node_depth),
        (x, y + tile_h / 2 + node_depth),
    ]
    right = [
        (x + tile_w, y + tile_h / 2),
        (x + tile_w / 2, y + tile_h),
        (x + tile_w / 2, y + tile_h + node_depth),
        (x + tile_w, y + tile_h / 2 + node_depth),
    ]
    return top, left, right


def _iso_render_faces(
    lines: list[str],
    *,
    top: list[tuple[float, float]],
    left: list[tuple[float, float]],
    right: list[tuple[float, float]],
    fill: str,
    stroke: str,
    left_fill: str,
    right_fill: str,
    node_depth: float,
) -> None:
    if node_depth > 0:
        lines.append(
            f'<polygon points="{" ".join(f"{px},{py}" for px, py in left)}" '
            f'fill="{left_fill}" stroke="{stroke}" stroke-width="1"/>'
        )
        lines.append(
            f'<polygon points="{" ".join(f"{px},{py}" for px, py in right)}" '
            f'fill="{right_fill}" stroke="{stroke}" stroke-width="1"/>'
        )
    lines.append(
        f'<polygon points="{" ".join(f"{px},{py}" for px, py in top)}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
    )


def _render_iso_port_label(
    lines: list[str],
    *,
    port_label: str,
    prefix: str,
    center_x: float,
    center_y: float,
    tile_w: float,
    tile_h: float,
    fill: str,
    stroke: str,
    left_fill: str,
    right_fill: str,
    font_size: int,
    theme: SvgTheme,
) -> tuple[float, float]:
    tile_width = tile_w
    tile_height = tile_h
    stack_depth = tile_h / 2
    label_center_x = center_x
    label_center_y = center_y - stack_depth
    top_points = _iso_tile_points(label_center_x, label_center_y, tile_width, tile_height)
    tile_points = _points_to_svg(top_points)
    bottom_points = [(px, py + stack_depth) for px, py in top_points]
    right_face = [
        top_points[1],
        top_points[2],
        bottom_points[2],
        bottom_points[1],
    ]
    left_face = [
        top_points[3],
        top_points[2],
        bottom_points[2],
        bottom_points[3],
    ]
    left_points = " ".join(f"{px},{py}" for px, py in left_face)
    right_points = " ".join(f"{px},{py}" for px, py in right_face)
    lines.append(
        f'<polygon class="label-tile-side" points="{left_points}" '
        f'fill="{left_fill}" stroke="{stroke}" stroke-width="1"/>'
    )
    lines.append(
        f'<polygon class="label-tile-side" points="{right_points}" '
        f'fill="{right_fill}" stroke="{stroke}" stroke-width="1"/>'
    )
    lines.append(
        f'<polygon class="label-tile" points="{tile_points}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
    )
    left_edge_top = top_points[0]
    left_edge_bottom = top_points[3]
    edge_len = math.hypot(
        left_edge_bottom[0] - left_edge_top[0],
        left_edge_bottom[1] - left_edge_top[1],
    )
    max_chars = max(6, int((edge_len * 0.85) / (font_size * 0.6)))
    front_lines = _format_port_label_lines(
        port_label,
        prefix=prefix,
        max_chars=max_chars,
    )
    if front_lines:
        text_x, text_y, edge_angle = _iso_front_text_position(top_points, tile_w, tile_h)
        _render_iso_text(
            lines,
            text_x=text_x,
            text_y=text_y,
            angle=edge_angle,
            text_lines=front_lines,
            font_size=font_size,
            fill=theme.text_secondary,
        )
    return label_center_x, label_center_y


def _iso_front_face_label_position(
    left_face: list[tuple[float, float]],
    tile_height: float,
    font_size: int,
) -> tuple[float, float, float]:
    """Position label on the front (left) face of an isometric node."""
    # left_face points: [top-left, top-right, bottom-right, bottom-left]
    # We want to center the text on this face
    top_left = left_face[0]
    top_right = left_face[1]
    bottom_right = left_face[2]
    bottom_left = left_face[3]

    # Center of the face
    center_x = (top_left[0] + top_right[0] + bottom_right[0] + bottom_left[0]) / 4
    center_y = (top_left[1] + top_right[1] + bottom_right[1] + bottom_left[1]) / 4

    # Angle follows the top edge of the left face (from top_left to top_right)
    angle = math.degrees(
        math.atan2(
            top_right[1] - top_left[1],
            top_right[0] - top_left[0],
        )
    )

    # Adjust position for better visual centering on the front face
    label_x = center_x - tile_height * 0.01
    label_y = center_y + font_size * 0.5 + tile_height * 0.04 - 6

    return label_x, label_y, angle


def _render_iso_node_icon(
    lines: list[str],
    *,
    icon_href: str | None,
    center_x: float,
    center_y: float,
    tile_w: float,
    tile_h: float,
    node_type: str,
    is_client: bool,
    port_label: str | None,
    port_prefix: str | None,
    fill: str,
    stroke: str,
    left_fill: str,
    right_fill: str,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    """Render the icon for an isometric node, including port label tile if needed."""
    icon_center_x = center_x
    icon_center_y = center_y
    iso_icon_size = min(tile_w, tile_h) * 1.26
    if port_label:
        font_size = max(options.font_size - 2, 8)
        prefix = port_prefix or "switch"
        icon_center_x, icon_center_y = _render_iso_port_label(
            lines,
            port_label=port_label,
            prefix=prefix,
            center_x=center_x,
            center_y=center_y,
            tile_w=tile_w,
            tile_h=tile_h,
            fill=fill,
            stroke=stroke,
            left_fill=left_fill,
            right_fill=right_fill,
            font_size=font_size,
            theme=theme,
        )
    if node_type == "ap":
        icon_center_y -= tile_h * 0.4
    if icon_href:
        icon_x = icon_center_x - iso_icon_size / 2
        icon_lift = tile_h * (0.02 if port_label else 0.04)
        icon_y = icon_center_y - iso_icon_size / 2 - icon_lift - tile_h * 0.05
        if is_client:
            icon_y -= tile_h * 0.05
        lines.append(
            f'<image href="{icon_href}" x="{icon_x}" y="{icon_y}" '
            f'width="{iso_icon_size}" height="{iso_icon_size}" '
            f'preserveAspectRatio="xMidYMid meet" filter="url(#iso-icon-emboss)"/>'
        )


def _render_iso_node_name(
    lines: list[str],
    *,
    name: str,
    top: list[tuple[float, float]],
    left: list[tuple[float, float]],
    tile_w: float,
    tile_h: float,
    port_label: str | None,
    node_depth: float,
    font_size: int,
    theme: SvgTheme,
) -> None:
    """Render the name label for an isometric node."""
    if not port_label and node_depth > 0:
        name_x, name_y, name_angle = _iso_front_face_label_position(
            left,
            tile_height=tile_h,
            font_size=font_size,
        )
    else:
        name_x, name_y, name_angle = _iso_name_label_position(
            top,
            tile_width=tile_w,
            tile_height=tile_h,
            font_size=font_size,
        )
    name_transform = (
        f"translate({name_x} {name_y}) rotate({name_angle}) skewX(30) "
        f"translate({-name_x} {-name_y})"
    )
    lines.append(
        f'<text x="{name_x}" y="{name_y}" class="node-label" text-anchor="middle" fill="{theme.text_primary}" '
        f'font-size="{font_size}" transform="{name_transform}">{_escape_text(name)}</text>'
    )


def _render_iso_node(
    lines: list[str],
    *,
    name: str,
    x: float,
    y: float,
    node_type: str,
    icons: dict[str, str],
    options: SvgOptions,
    port_label: str | None,
    port_prefix: str | None,
    layout: IsoLayout,
    theme: SvgTheme,
) -> None:
    fill, stroke = _TYPE_COLORS.get(node_type, _TYPE_COLORS["other"])
    fill = f"url(#iso-node-{node_type})"
    tile_w = layout.tile_width
    tile_h = layout.tile_height

    # Determine node depth based on port label presence
    is_client = node_type in ("client", "client_cluster")
    if port_label:
        # Nodes with port labels: no 3D base box, only the port label tile
        node_depth = 0.0
    else:
        # Nodes without port labels: consistent 3D depth
        node_depth = layout.tile_height * 0.15

    group_attrs = _svg_node_group_attrs(None, name, node_type)
    lines.append(f"<g{group_attrs}>")
    lines.append(f"<title>{_escape_text(name)}</title>")
    top, left, right = _iso_node_polygons(x, y, tile_w, tile_h, node_depth)
    lines.append(
        f'<polygon points="{_points_to_svg(top)}" fill="transparent" '
        'pointer-events="all" class="node-hitbox"/>'
    )
    left_fill = theme.node_side_left
    right_fill = theme.node_side_right
    _iso_render_faces(
        lines,
        top=top,
        left=left,
        right=right,
        fill=fill,
        stroke=stroke,
        left_fill=left_fill,
        right_fill=right_fill,
        node_depth=node_depth,
    )
    _render_iso_node_icon(
        lines,
        icon_href=icons.get(node_type, icons.get("other")),
        center_x=x + tile_w / 2,
        center_y=y + tile_h / 2,
        tile_w=tile_w,
        tile_h=tile_h,
        node_type=node_type,
        is_client=is_client,
        port_label=port_label,
        port_prefix=port_prefix,
        fill=fill,
        stroke=stroke,
        left_fill=left_fill,
        right_fill=right_fill,
        options=options,
        theme=theme,
    )
    _render_iso_node_name(
        lines,
        name=name,
        top=top,
        left=left,
        tile_w=tile_w,
        tile_h=tile_h,
        port_label=port_label,
        node_depth=node_depth,
        font_size=max(options.font_size - 2, 8),
        theme=theme,
    )
    lines.append("</g>")


def _render_iso_nodes(
    lines: list[str],
    *,
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    icons: dict[str, str],
    options: SvgOptions,
    layout: IsoLayout,
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
    theme: SvgTheme,
) -> None:
    for name, (x, y) in positions.items():
        _render_iso_node(
            lines,
            name=name,
            x=x,
            y=y,
            node_type=node_types.get(name, "other"),
            icons=icons,
            options=options,
            port_label=node_port_labels.get(name),
            port_prefix=node_port_prefix.get(name),
            layout=layout,
            theme=theme,
        )
