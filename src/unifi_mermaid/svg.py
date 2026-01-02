"""SVG rendering for orthogonal network diagrams."""

from __future__ import annotations

import base64
import math
from dataclasses import dataclass
from pathlib import Path

from .topology import Edge


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


_TYPE_ORDER = ["gateway", "switch", "ap", "client", "other"]
_ICON_FILES = {
    "gateway": "router-network.svg",
    "switch": "server-network.svg",
    "ap": "access-point.svg",
    "client": "laptop.svg",
    "other": "server.svg",
}

_TYPE_COLORS = {
    "gateway": ("#ffe3b3", "#d98300"),
    "switch": ("#d6ecff", "#3a7bd5"),
    "ap": ("#d7f5e7", "#27ae60"),
    "client": ("#f2e5ff", "#7f3fbf"),
    "other": ("#eeeeee", "#8f8f8f"),
}


def _escape_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _extract_port_text(side: str) -> str | None:
    candidate = side.split(":", 1)[1].strip() if ":" in side else side.strip()
    if candidate.lower().startswith("port "):
        return candidate
    return None


def _extract_device_name(side: str) -> str | None:
    if ":" not in side:
        return None
    name = side.split(":", 1)[0].strip()
    return name or None


def _compact_edge_label(
    label: str, *, left_node: str | None = None, right_node: str | None = None
) -> str:
    if "<->" not in label:
        return label
    left, right = (part.strip() for part in label.split("<->", 1))
    left_name = _extract_device_name(left)
    right_name = _extract_device_name(right)
    left_port = _extract_port_text(left)
    right_port = _extract_port_text(right)
    if left_node and right_node:
        if right_name and right_name == left_node and left_name == right_node:
            left, right = right, left
            left_name, right_name = right_name, left_name
            left_port, right_port = right_port, left_port
    if left_port and right_port:
        if left_name:
            return f"{left_name} {left_port} <-> {right_port}"
        return f"{left_port} <-> {right_port}"
    if left_port:
        return left_port
    if right_port:
        return right_port
    return label


def _wrap_text(label: str, *, max_len: int = 24) -> list[str]:
    if len(label) <= max_len:
        return [label]
    split_at = label.rfind(" ", 0, max_len + 1)
    if split_at == -1:
        split_at = max_len
    first = label[:split_at].rstrip()
    rest = label[split_at:].lstrip()
    return [first, rest] if rest else [first]


def _label_metrics(
    lines: list[str], *, font_size: int, padding_x: int = 6, padding_y: int = 3
) -> tuple[float, float]:
    max_len = max((len(line) for line in lines), default=0)
    text_width = max_len * font_size * 0.6
    text_height = len(lines) * (font_size + 2)
    width = text_width + padding_x * 2
    height = text_height + padding_y * 2
    return width, height


def _load_icons() -> dict[str, str]:
    base = Path(__file__).resolve().parent / "assets" / "icons"
    icons: dict[str, str] = {}
    for node_type, filename in _ICON_FILES.items():
        path = base / filename
        if not path.exists():
            continue
        data = path.read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        icons[node_type] = f"data:image/svg+xml;base64,{encoded}"
    return icons


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


def _tree_layout_indices(
    edges: list[Edge], node_types: dict[str, str]
) -> tuple[dict[str, float], dict[str, int]]:
    nodes = set(node_types.keys())
    for edge in edges:
        nodes.add(edge.left)
        nodes.add(edge.right)

    children: dict[str, list[str]] = {name: [] for name in nodes}
    incoming: dict[str, int] = {name: 0 for name in nodes}
    for edge in edges:
        children[edge.left].append(edge.right)
        incoming[edge.right] = incoming.get(edge.right, 0) + 1

    type_order = {t: i for i, t in enumerate(_TYPE_ORDER)}

    def sort_key(name: str) -> tuple[int, str]:
        return (type_order.get(node_types.get(name, "other"), 99), name.lower())

    for _parent, child_list in children.items():
        child_list.sort(key=sort_key)

    gateways = [n for n, t in node_types.items() if t == "gateway"]
    roots = gateways if gateways else [n for n in nodes if incoming.get(n, 0) == 0]
    if not roots:
        roots = list(nodes)
    roots = sorted(roots, key=sort_key)

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


def render_svg(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    options: SvgOptions | None = None,
) -> str:
    options = options or SvgOptions()
    icons = _load_icons()
    positions, width, height = _layout_nodes(edges, node_types, options)
    out_width = options.width or width
    out_height = options.height or height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{out_width}" height="{out_height}" '
        f'viewBox="0 0 {width} {height}">',
        f"<style>text{{font-family:Arial,Helvetica,sans-serif;font-size:{options.font_size}px;}}</style>",
    ]

    node_port_labels: dict[str, str] = {}
    for edge in edges:
        if edge.left not in positions or edge.right not in positions:
            continue
        src_x, src_y = positions[edge.left]
        dst_x, dst_y = positions[edge.right]
        src_cx = src_x + options.node_width / 2
        dst_cx = dst_x + options.node_width / 2
        src_bottom = src_y + options.node_height
        dst_top = dst_y
        mid_y = (src_bottom + dst_top) / 2
        color = "#1e88e5" if edge.poe else "#9aa0a6"
        width_px = 2 if edge.poe else 1
        path = f"M {src_cx} {src_bottom} L {src_cx} {mid_y} L {dst_cx} {mid_y} L {dst_cx} {dst_top}"
        lines.append(f'<path d="{path}" stroke="{color}" stroke-width="{width_px}" fill="none"/>')
        if edge.poe:
            icon_x = dst_cx
            icon_y = dst_top - 6
            lines.append(
                f'<text x="{icon_x}" y="{icon_y}" text-anchor="middle" fill="#1e88e5" '
                f'font-size="{max(options.font_size, 10)}">⚡</text>'
            )

        if edge.label:
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
            else:
                upstream_part = edge.label.split("<->", 1)[0].strip()
                upstream_name = _extract_device_name(upstream_part) or edge.left
                if label_text.lower().startswith("port "):
                    label_text = f"{upstream_name} {label_text}"
                node_port_labels.setdefault(edge.right, label_text)

    for name, (x, y) in positions.items():
        node_type = node_types.get(name, "other")
        fill, stroke = _TYPE_COLORS.get(node_type, _TYPE_COLORS["other"])
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
                f'text-anchor="start" fill="#555" font-size="{font_size}">'
            )
            for idx, line in enumerate(wrapped):
                dy = 0 if idx == 0 else line_height
                lines.append(f'<tspan x="{text_x}" dy="{dy}">{_escape_text(line)}</tspan>')
            lines.append("</text>")
        lines.append(
            f'<text x="{text_x}" y="{text_y}" fill="#1f1f1f" text-anchor="start">{safe_name}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_svg_isometric(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    options: SvgOptions | None = None,
) -> str:
    options = options or SvgOptions()
    icons = _load_icons()
    positions_index, levels = _tree_layout_indices(edges, node_types)
    if not positions_index:
        positions_index = {}
    tile_w = options.node_width
    tile_h = options.node_height
    step_w = tile_w
    step_h = tile_h
    grid_spacing_x = max(2, 1 + int(round(options.h_gap / max(tile_w, 1))))
    grid_spacing_y = max(2, 1 + int(round(options.v_gap / max(tile_h, 1))))

    grid_positions: dict[str, tuple[float, float]] = {}
    positions: dict[str, tuple[float, float]] = {}

    def project_iso(gx: float, gy: float) -> tuple[float, float]:
        iso_x = (gx - gy) * (step_w / 2)
        iso_y = (gx + gy) * (step_h / 2)
        return iso_x, iso_y

    def project_iso_center(gx: float, gy: float) -> tuple[float, float]:
        return project_iso(gx + 0.5, gy + 0.5)

    for name, idx in positions_index.items():
        level = levels.get(name, 0)
        gx = round(idx * grid_spacing_x)
        gy = round(float(level) * grid_spacing_y)
        grid_positions[name] = (float(gx), float(gy))
        iso_x, iso_y = project_iso_center(float(gx), float(gy))
        positions[name] = (iso_x, iso_y)

    if positions:
        min_x = min(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        max_x = max(x for x, _ in positions.values())
        max_y = max(y for _, y in positions.values())
    else:
        min_x = min_y = 0.0
        max_x = max_y = 0.0

    padding = options.padding
    offset_x = -min_x + padding
    offset_y = -min_y + padding
    for name, (x, y) in positions.items():
        positions[name] = (x + offset_x, y + offset_y)

    def project_iso_center_padded(gx: float, gy: float) -> tuple[float, float]:
        iso_x, iso_y = project_iso_center(gx, gy)
        return iso_x + offset_x, iso_y + offset_y

    def grid_center(gx: float, gy: float) -> tuple[float, float]:
        cx, cy = project_iso_center_padded(gx, gy)
        return cx + tile_w / 2, cy + tile_h / 2

    def front_anchor(gx: float, gy: float) -> tuple[float, float]:
        cx, cy = grid_center(gx, gy)
        return cx, cy + tile_h / 2

    width = max_x - min_x + tile_w + padding * 2
    height = max_y - min_y + tile_h + padding * 2

    out_width = options.width or int(width)
    out_height = options.height or int(height)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{out_width}" height="{out_height}" '
        f'viewBox="0 0 {width} {height}">',
        f"<style>text{{font-family:Arial,Helvetica,sans-serif;font-size:{options.font_size}px;}}</style>",
    ]

    if grid_positions:
        min_gx = min(gx for gx, _ in grid_positions.values())
        max_gx = max(gx for gx, _ in grid_positions.values())
        min_gy = min(gy for _, gy in grid_positions.values())
        max_gy = max(gy for _, gy in grid_positions.values())
        pad = 12
        gx_start = int(math.floor(min_gx)) - pad
        gx_end = int(math.ceil(max_gx)) + pad
        gy_start = int(math.floor(min_gy)) - pad
        gy_end = int(math.ceil(max_gy)) + pad
        grid_lines: list[str] = []
        for gx in range(gx_start, gx_end + 1):
            x1, y1 = project_iso(float(gx), float(gy_start))
            x2, y2 = project_iso(float(gx), float(gy_end))
            x1 += padding
            y1 += padding
            x2 += padding
            y2 += padding
            grid_lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#efefef" stroke-width="0.6"/>'
            )
        for gy in range(gy_start, gy_end + 1):
            x1, y1 = project_iso(float(gx_start), float(gy))
            x2, y2 = project_iso(float(gx_end), float(gy))
            x1 += padding
            y1 += padding
            x2 += padding
            y2 += padding
            grid_lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#efefef" stroke-width="0.6"/>'
            )
        lines.append('<g class="iso-grid" opacity="0.7">')
        lines.extend(grid_lines)
        lines.append("</g>")

    node_port_labels: dict[str, str] = {}

    def iso_tile_points(cx: float, cy: float, width: float, height: float) -> str:
        points = [
            (cx, cy - height / 2),
            (cx + width / 2, cy),
            (cx, cy + height / 2),
            (cx - width / 2, cy),
        ]
        return " ".join(f"{px},{py}" for px, py in points)

    for edge in edges:
        if edge.left not in positions or edge.right not in positions:
            continue
        src_grid = grid_positions.get(edge.left)
        dst_grid = grid_positions.get(edge.right)
        if not src_grid or not dst_grid:
            continue
        color = "#1e88e5" if edge.poe else "#2e7d32"
        width_px = 5 if edge.poe else 4
        src_gx, src_gy = float(src_grid[0]), float(src_grid[1])
        dst_gx, dst_gy = float(dst_grid[0]), float(dst_grid[1])
        dx = dst_gx - src_gx
        dy = dst_gy - src_gy
        src_cx, src_cy = front_anchor(src_gx, src_gy)
        dst_cx, dst_cy = front_anchor(dst_gx, dst_gy)
        path_cmds: list[str] = []
        if dx == 0 or dy == 0:
            path_cmds = [f"M {src_cx} {src_cy}", f"L {dst_cx} {dst_cy}"]
        else:
            elbow_gx, elbow_gy = dst_gx, src_gy
            elbow_cx, elbow_cy = front_anchor(elbow_gx, elbow_gy)
            path_cmds = [
                f"M {src_cx} {src_cy}",
                f"L {elbow_cx} {elbow_cy}",
                f"L {dst_cx} {dst_cy}",
            ]
        path = " ".join(path_cmds)
        lines.append(
            f'<path d="{path}" stroke="{color}" stroke-width="{width_px}" '
            f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        if edge.poe:
            icon_x = dst_cx
            icon_y = dst_cy - tile_h * 0.4
            lines.append(
                f'<text x="{icon_x}" y="{icon_y}" text-anchor="middle" fill="#1e88e5" '
                f'font-size="{max(options.font_size, 10)}">⚡</text>'
            )
        if edge.label:
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
            else:
                upstream_part = edge.label.split("<->", 1)[0].strip()
                upstream_name = _extract_device_name(upstream_part) or edge.left
                if label_text.lower().startswith("port "):
                    label_text = f"{upstream_name} {label_text}"
                node_port_labels.setdefault(edge.right, label_text)

    for name, (x, y) in positions.items():
        node_type = node_types.get(name, "other")
        fill, stroke = _TYPE_COLORS.get(node_type, _TYPE_COLORS["other"])
        top = [
            (x + tile_w / 2, y),
            (x + tile_w, y + tile_h / 2),
            (x + tile_w / 2, y + tile_h),
            (x, y + tile_h / 2),
        ]
        left = [
            (x, y + tile_h / 2),
            (x + tile_w / 2, y + tile_h),
            (x + tile_w / 2, y + tile_h + tile_h / 2),
            (x, y + tile_h / 2 + tile_h / 2),
        ]
        right = [
            (x + tile_w, y + tile_h / 2),
            (x + tile_w / 2, y + tile_h),
            (x + tile_w / 2, y + tile_h + tile_h / 2),
            (x + tile_w, y + tile_h / 2 + tile_h / 2),
        ]
        left_fill = "#d0d0d0" if node_type == "other" else "#dcdcdc"
        right_fill = "#c2c2c2" if node_type == "other" else "#c8c8c8"
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

        icon_href = icons.get(node_type, icons.get("other"))
        center_x = x + tile_w / 2
        center_y = y + tile_h / 2
        if icon_href:
            icon_x = center_x - options.icon_size / 2
            icon_y = center_y - options.icon_size / 2
            lines.append(
                f'<image href="{icon_href}" x="{icon_x}" y="{icon_y}" '
                f'width="{options.icon_size}" height="{options.icon_size}"/>'
            )
            text_y = center_y + options.icon_size / 2 + options.font_size
        else:
            text_y = center_y + options.font_size

        port_label = node_port_labels.get(name)
        if port_label:
            font_size = max(options.font_size - 2, 8)
            wrapped = _wrap_text(port_label)
            label_width, label_height = _label_metrics(
                wrapped, font_size=font_size, padding_x=8, padding_y=4
            )
            tile_height = max(label_width / 2, label_height + 6)
            tile_points = iso_tile_points(center_x, text_y, label_width, tile_height)
            lines.append(
                f'<polygon class="label-tile" points="{tile_points}" '
                f'fill="#ffffff" stroke="#c0c0c0" stroke-width="1"/>'
            )
            lines.append(
                f'<text x="{center_x}" y="{text_y}" text-anchor="middle" fill="#555" '
                f'font-size="{font_size}">'
            )
            for idx, line in enumerate(wrapped):
                dy = 0 if idx == 0 else font_size + 2
                lines.append(f'<tspan x="{center_x}" dy="{dy}">{_escape_text(line)}</tspan>')
            lines.append("</text>")
            text_y = text_y + max(tile_height / 2, label_height) + 6

        lines.append(
            f'<text x="{center_x}" y="{text_y}" text-anchor="middle" fill="#1f1f1f">'
            f"{_escape_text(name)}</text>"
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"
