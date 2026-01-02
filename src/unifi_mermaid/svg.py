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


def _compact_edge_label(label: str) -> str:
    if "<->" not in label:
        return label
    left, right = (part.strip() for part in label.split("<->", 1))
    left_port = _extract_port_text(left)
    right_port = _extract_port_text(right)
    if left_port and right_port:
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
    max_level = 0

    def dfs(node: str, level: int) -> float:
        nonlocal cursor, max_level
        if node in positions_index:
            return positions_index[node]
        visited.add(node)
        levels[node] = min(levels.get(node, level), level)
        max_level = max(max_level, level)
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
    height = (
        options.padding * 2
        + (max_level + 1) * options.node_height
        + max(0, max_level) * options.v_gap
    )
    return positions, width, height


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

    client_port_labels: dict[str, str] = {}
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
        color = "#2ecc71" if edge.poe else "#9aa0a6"
        width_px = 2 if edge.poe else 1
        path = f"M {src_cx} {src_bottom} L {src_cx} {mid_y} L {dst_cx} {mid_y} L {dst_cx} {dst_top}"
        lines.append(f'<path d="{path}" stroke="{color}" stroke-width="{width_px}" fill="none"/>')

        if edge.label:
            label_x = (src_cx + dst_cx) / 2
            label_y = mid_y - 4
            label_text = _compact_edge_label(edge.label)
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
                    client_port_labels.setdefault(client_node, f"{upstream_name}: {port_text}")
                else:
                    label = _escape_text(label_text)
                    lines.append(
                        f'<text x="{label_x}" y="{label_y}" text-anchor="middle" fill="#555">{label}</text>'
                    )
            else:
                label = _escape_text(label_text)
                lines.append(
                    f'<text x="{label_x}" y="{label_y}" text-anchor="middle" fill="#555">{label}</text>'
                )

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
        if node_type == "client":
            text_y = y + options.node_height - 6
        else:
            text_y = y + options.node_height / 2 + options.font_size / 2 - 2
        safe_name = _escape_text(name)
        if node_type == "client":
            port_label = client_port_labels.get(name)
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
