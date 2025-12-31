"""SVG rendering for orthogonal network diagrams."""

from __future__ import annotations

import base64
from collections import deque
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

    gateways = [n for n, t in node_types.items() if t == "gateway"]
    roots = gateways if gateways else [n for n in nodes if incoming.get(n, 0) == 0]
    if not roots:
        roots = list(nodes)

    levels: dict[str, int] = {}
    queue: deque[str] = deque()
    for root in roots:
        levels[root] = 0
        queue.append(root)

    while queue:
        current = queue.popleft()
        for child in children.get(current, []):
            if child in levels:
                continue
            levels[child] = levels[current] + 1
            queue.append(child)

    max_level = max(levels.values(), default=0)
    level_nodes: dict[int, list[str]] = {i: [] for i in range(max_level + 1)}
    for node, level in levels.items():
        level_nodes[level].append(node)

    type_order = {t: i for i, t in enumerate(_TYPE_ORDER)}
    for level, names in level_nodes.items():
        names.sort(key=lambda n: (type_order.get(node_types.get(n, "other"), 99), n.lower()))
        level_nodes[level] = names

    positions: dict[str, tuple[float, float]] = {}
    for level, names in level_nodes.items():
        for idx, name in enumerate(names):
            x = options.padding + idx * (options.node_width + options.h_gap)
            y = options.padding + level * (options.node_height + options.v_gap)
            positions[name] = (x, y)

    max_nodes = max((len(n) for n in level_nodes.values()), default=1)
    width = (
        options.padding * 2 + max_nodes * options.node_width + max(0, max_nodes - 1) * options.h_gap
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
            lines.append(
                f'<text x="{label_x}" y="{label_y}" text-anchor="middle" fill="#555">{edge.label}</text>'
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
        text_y = y + options.node_height / 2 + options.font_size / 2 - 2
        lines.append(
            f'<text x="{text_x}" y="{text_y}" fill="#1f1f1f" text-anchor="start">{name}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"
