"""Shared isometric geometry primitives and layout dataclass."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .svg_labels import _escape_text


@dataclass(frozen=True)
class IsoLayout:
    iso_angle: float
    tile_width: float
    tile_height: float
    step_width: float
    step_height: float
    grid_spacing_x: int
    grid_spacing_y: int
    padding: float
    tile_y_offset: float
    extra_pad: float


def _iso_tile_points(
    center_x: float, center_y: float, width: float, height: float
) -> list[tuple[float, float]]:
    return [
        (center_x, center_y - height / 2),
        (center_x + width / 2, center_y),
        (center_x, center_y + height / 2),
        (center_x - width / 2, center_y),
    ]


def _points_to_svg(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{px},{py}" for px, py in points)


def _iso_front_text_position(
    top_points: list[tuple[float, float]], tile_width: float, tile_height: float
) -> tuple[float, float, float]:
    left_edge_top = top_points[0]
    left_edge_bottom = top_points[3]
    edge_mid_x = (left_edge_top[0] + left_edge_bottom[0]) / 2
    edge_mid_y = (left_edge_top[1] + left_edge_bottom[1]) / 2
    center_x = sum(px for px, _py in top_points) / len(top_points)
    center_y = sum(py for _px, py in top_points) / len(top_points)
    normal_x = center_x - edge_mid_x
    normal_y = center_y - edge_mid_y
    normal_len = math.hypot(normal_x, normal_y) or 1.0
    normal_x /= normal_len
    normal_y /= normal_len
    inset = tile_height * 0.27
    text_x = edge_mid_x + normal_x * inset + tile_width * 0.02
    text_y = edge_mid_y + normal_y * inset + tile_height * 0.33
    edge_dx = left_edge_bottom[0] - left_edge_top[0]
    edge_dy = left_edge_bottom[1] - left_edge_top[1]
    edge_len = math.hypot(edge_dx, edge_dy) or 1.0
    edge_dx /= edge_len
    edge_dy /= edge_len
    slide = tile_height * 0.32
    text_x += edge_dx * slide
    text_y += edge_dy * slide
    name_edge_left = top_points[3]
    name_edge_right = top_points[2]
    angle = math.degrees(
        math.atan2(
            name_edge_right[1] - name_edge_left[1],
            name_edge_right[0] - name_edge_left[0],
        )
    )
    return text_x, text_y, angle


def _render_iso_text(
    lines: list[str],
    *,
    text_x: float,
    text_y: float,
    angle: float,
    text_lines: list[str],
    font_size: int,
    fill: str,
) -> None:
    line_height = font_size + 2
    start_y = text_y - (len(text_lines) - 1) * line_height / 2
    text_transform = (
        f"translate({text_x} {start_y}) rotate({angle}) skewX(30) translate({-text_x} {-start_y})"
    )
    lines.append(
        f'<text x="{text_x}" y="{start_y}" text-anchor="middle" fill="{fill}" '
        f'font-size="{font_size}" font-style="normal" '
        f'transform="{text_transform}">'
    )
    for idx, line in enumerate(text_lines):
        dy = 0 if idx == 0 else line_height
        lines.append(f'<tspan x="{text_x}" dy="{dy}">{_escape_text(line)}</tspan>')
    lines.append("</text>")


def _iso_name_label_position(
    top_points: list[tuple[float, float]],
    *,
    tile_width: float,
    tile_height: float,
    font_size: int,
) -> tuple[float, float, float]:
    name_edge_left = top_points[3]
    name_edge_right = top_points[2]
    name_mid_x = (name_edge_left[0] + name_edge_right[0]) / 2
    name_mid_y = (name_edge_left[1] + name_edge_right[1]) / 2
    name_center_x = sum(px for px, _py in top_points) / len(top_points)
    name_center_y = sum(py for _px, py in top_points) / len(top_points)
    name_normal_x = name_center_x - name_mid_x
    name_normal_y = name_center_y - name_mid_y
    name_normal_len = math.hypot(name_normal_x, name_normal_y) or 1.0
    name_normal_x /= name_normal_len
    name_normal_y /= name_normal_len
    name_inset = tile_height * 0.13
    name_x = name_mid_x + name_normal_x * name_inset - tile_width * 0.08
    name_y = name_mid_y + name_normal_y * name_inset + font_size - tile_height * 0.05
    name_angle = math.degrees(
        math.atan2(
            name_edge_right[1] - name_edge_left[1],
            name_edge_right[0] - name_edge_left[0],
        )
    )
    return name_x, name_y, name_angle


def _iso_project(layout: IsoLayout, gx: float, gy: float) -> tuple[float, float]:
    iso_x = (gx - gy) * (layout.step_width / 2)
    iso_y = (gx + gy) * (layout.step_height / 2)
    return iso_x, iso_y


def _iso_project_center(layout: IsoLayout, gx: float, gy: float) -> tuple[float, float]:
    return _iso_project(layout, gx + 0.5, gy + 0.5)
