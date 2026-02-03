"""SVG rendering for orthogonal network diagrams."""

from __future__ import annotations

import base64
import math
from collections.abc import Callable
from dataclasses import dataclass
from html import escape as _escape_attr
from pathlib import Path

from ..model.topology import Edge, WanInfo, WanInterface
from .svg_theme import DEFAULT_THEME, SvgTheme, svg_defs


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


@dataclass(frozen=True)
class IsoLayoutPositions:
    layout: IsoLayout
    grid_positions: dict[str, tuple[float, float]]
    positions: dict[str, tuple[float, float]]
    width: float
    height: float
    offset_x: float
    offset_y: float


def _iso_layout(options: SvgOptions) -> IsoLayout:
    tile_width = options.node_width * 1.5
    iso_angle = math.radians(30.0)
    tile_height = tile_width * math.tan(iso_angle)
    step_width = tile_width
    step_height = tile_height
    grid_spacing_x = max(2, 1 + int(round(options.h_gap / max(tile_width, 1))))
    grid_spacing_y = max(2, 1 + int(round(options.v_gap / max(tile_height, 1))))
    padding = float(options.padding)
    tile_y_offset = tile_height / 2
    extra_pad = max(12.0, tile_width * 0.35)
    return IsoLayout(
        iso_angle=iso_angle,
        tile_width=tile_width,
        tile_height=tile_height,
        step_width=step_width,
        step_height=step_height,
        grid_spacing_x=grid_spacing_x,
        grid_spacing_y=grid_spacing_y,
        padding=padding,
        tile_y_offset=tile_y_offset,
        extra_pad=extra_pad,
    )


_TYPE_ORDER = ["gateway", "switch", "ap", "client", "client_cluster", "other"]
# Icon file mappings per icon set
# Legacy set uses existing icons from root and isometric/ directories
_ICON_FILES_LEGACY = {
    "gateway": "router-network.svg",
    "switch": "server-network.svg",
    "ap": "access-point.svg",
    "client": "laptop.svg",
    "client_cluster": "laptop.svg",
    "other": "server.svg",
}

_ISO_ICON_FILES_LEGACY = {
    "gateway": "router.svg",
    "switch": "switch-module.svg",
    "ap": "tower.svg",
    "client": "laptop.svg",
    "client_cluster": "laptop.svg",
    "other": "server.svg",
}

# Modern set uses consistent naming in modern/ directory
_ICON_FILES_MODERN = {
    "gateway": "gateway.svg",
    "switch": "switch.svg",
    "ap": "ap.svg",
    "client": "client.svg",
    "client_cluster": "client.svg",
    "other": "other.svg",
}

# Icon set registry: maps set names to (flat_dir, iso_dir, flat_files, iso_files)
_ICON_SETS = {
    "legacy": (
        "",  # Flat icons in root icons/ directory
        "isometric",  # Isometric icons in isometric/ subdirectory
        _ICON_FILES_LEGACY,
        _ISO_ICON_FILES_LEGACY,
    ),
    "modern": (
        "modern",  # Both flat and iso use same directory
        "modern",
        _ICON_FILES_MODERN,
        _ICON_FILES_MODERN,  # Same files for both (isometric style)
    ),
}

# Backwards compatibility aliases
_ICON_FILES = _ICON_FILES_LEGACY
_ISO_ICON_FILES = _ISO_ICON_FILES_LEGACY

_TYPE_COLORS = {
    "gateway": ("#ffd199", "#f08a00"),
    "switch": ("#bfe4ff", "#1c6dd0"),
    "ap": ("#c4f2d4", "#1f9a50"),
    "client": ("#e4ccff", "#6b2fb4"),
    "client_cluster": ("#d4b8ff", "#5a25a0"),  # Slightly darker purple for clusters
    "other": ("#e3e3e3", "#7b7b7b"),
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
    left_segment, right_segment = (part.strip() for part in label.split("<->", 1))
    left_name = _extract_device_name(left_segment)
    right_name = _extract_device_name(right_segment)
    left_port = _extract_port_text(left_segment)
    right_port = _extract_port_text(right_segment)
    if left_node and right_node:
        if right_name and right_name == left_node and left_name == right_node:
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


def _format_port_label_lines(
    port_label: str,
    *,
    node_type: str,
    prefix: str,
    max_chars: int,
) -> list[str]:
    def _port_only(segment: str) -> str:
        port = _extract_port_text(segment)
        if port:
            return port
        lower = segment.lower()
        idx = lower.rfind("port ")
        if idx != -1:
            return segment[idx:].strip()
        return segment.split(":", 1)[-1].strip()

    def _truncate(text: str, max_len: int = max_chars) -> str:
        return text[: max_len - 3].rstrip() + "..." if len(text) > max_len else text

    if "<->" in port_label:
        left_part, right_part = (part.strip() for part in port_label.split("<->", 1))
        front_text = _truncate(f"{prefix}: {_port_only(left_part)}")
        side_prefix = prefix if node_type == "client" else "local"
        side_text = _truncate(f"{side_prefix}: {_port_only(right_part)}")
        return [line for line in (front_text, side_text) if line]
    side_prefix = prefix if node_type == "client" else "local"
    side_text = _truncate(f"{side_prefix}: {_port_only(port_label)}")
    return [side_text]


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


def _wrap_text(label: str, *, max_len: int = 24) -> list[str]:
    if len(label) <= max_len:
        return [label]
    split_at = label.rfind(" ", 0, max_len + 1)
    if split_at == -1:
        split_at = max_len
    first = label[:split_at].rstrip()
    rest = label[split_at:].lstrip()
    return [first, rest] if rest else [first]


def _shorten_prefix(name: str, max_words: int = 2) -> str:
    words = name.split()
    if len(words) <= max_words:
        return name
    return " ".join(words[:max_words]) + "..."


def _label_metrics(
    lines: list[str], *, font_size: int, padding_x: int = 6, padding_y: int = 3
) -> tuple[float, float]:
    max_len = max((len(line) for line in lines), default=0)
    text_width = max_len * font_size * 0.6
    text_height = len(lines) * (font_size + 2)
    width = text_width + padding_x * 2
    height = text_height + padding_y * 2
    return width, height


def _load_icons(icon_set: str = "legacy") -> dict[str, str]:
    """Load flat (non-isometric) icons for the specified icon set.

    Falls back to legacy icons if the requested icon is not found in the set.
    """
    base = Path(__file__).resolve().parents[1] / "assets" / "icons"
    icons: dict[str, str] = {}

    # Get set configuration, defaulting to legacy
    set_config = _ICON_SETS.get(icon_set, _ICON_SETS["legacy"])
    subdir, _, file_map, _ = set_config

    # Also load legacy for fallback
    legacy_config = _ICON_SETS["legacy"]
    legacy_subdir, _, legacy_files, _ = legacy_config

    for node_type in _ICON_FILES_LEGACY.keys():
        # Try requested set first
        filename = file_map.get(node_type)
        if filename:
            path = base / subdir / filename if subdir else base / filename
            if path.exists():
                data = path.read_bytes()
                encoded = base64.b64encode(data).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"
                continue

        # Fallback to legacy
        legacy_filename = legacy_files.get(node_type)
        if legacy_filename:
            legacy_path = (
                base / legacy_subdir / legacy_filename if legacy_subdir else base / legacy_filename
            )
            if legacy_path.exists():
                data = legacy_path.read_bytes()
                encoded = base64.b64encode(data).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"

    return icons


def _load_isometric_icons(icon_set: str = "legacy", decal_color: str = "#5A6878") -> dict[str, str]:
    """Load isometric icons for the specified icon set.

    Falls back to legacy icons if the requested icon is not found in the set.
    Modern icons use #DECAL0 as placeholder which gets replaced with decal_color.
    """
    base = Path(__file__).resolve().parents[1] / "assets" / "icons"
    icons: dict[str, str] = {}

    # Get set configuration, defaulting to legacy
    set_config = _ICON_SETS.get(icon_set, _ICON_SETS["legacy"])
    _, iso_subdir, _, iso_file_map = set_config

    # Also load legacy for fallback
    legacy_config = _ICON_SETS["legacy"]
    _, legacy_iso_subdir, _, legacy_iso_files = legacy_config

    for node_type in _ISO_ICON_FILES_LEGACY.keys():
        # Try requested set first
        filename = iso_file_map.get(node_type)
        if filename:
            path = base / iso_subdir / filename
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # Replace placeholder color with theme color
                content = content.replace("#DECAL0", decal_color)
                data = content.encode("utf-8")
                encoded = base64.b64encode(data).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"
                continue

        # Fallback to legacy
        legacy_filename = legacy_iso_files.get(node_type)
        if legacy_filename:
            legacy_path = base / legacy_iso_subdir / legacy_filename
            if legacy_path.exists():
                data = legacy_path.read_bytes()
                encoded = base64.b64encode(data).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"

    return icons


def _format_wan_speed(speed_mbps: int | None) -> str | None:
    """Format speed in Mbps to human-readable string (e.g., 10GbE, 100MbE)."""
    if speed_mbps is None or speed_mbps == 0:
        return None
    if speed_mbps >= 1000:
        gbps = speed_mbps / 1000
        if gbps == int(gbps):
            return f"{int(gbps)}GbE"
        return f"{gbps:.1f}GbE"
    return f"{speed_mbps}MbE"


def _format_wan_interface_line(
    wan: WanInterface,
    prefix: str,
    *,
    is_dual: bool,
    include_speed: bool = True,
) -> str:
    """Format a single WAN interface line."""
    status = "●" if wan.enabled else "○"
    label = wan.label or prefix
    speed_parts = []
    if include_speed and wan.link_speed and wan.enabled:
        speed_parts.append(f"Link {_format_wan_speed(wan.link_speed)}")
    if wan.isp_speed:
        speed_parts.append(f"ISP {wan.isp_speed}")
    speed_str = " / ".join(speed_parts) if speed_parts else ""

    if not wan.enabled and prefix == "WAN2":
        return f"{prefix}: {label} (disabled) {status}"

    if is_dual:
        line = f"{prefix}: {label}"
        if speed_str:
            line += f" ({speed_str})"
        return f"{line} {status}"

    return label


def _build_wan_label_lines(wan_info: WanInfo) -> list[str]:
    """Build label lines for WAN display."""
    label_lines: list[str] = []
    is_dual = wan_info.wan2 is not None

    if wan_info.wan1:
        wan1 = wan_info.wan1
        if is_dual:
            label_lines.append(
                _format_wan_interface_line(wan1, "WAN1", is_dual=True, include_speed=True)
            )
        else:
            # Single WAN format: multi-line
            label_lines.append(wan1.label or "WAN1")
            speed_parts = []
            if wan1.link_speed:
                speed_parts.append(f"Link {_format_wan_speed(wan1.link_speed)}")
            if wan1.isp_speed:
                speed_parts.append(f"ISP {wan1.isp_speed}")
            if speed_parts:
                label_lines.append(" / ".join(speed_parts))
            if wan1.ip_address:
                label_lines.append(wan1.ip_address)

    if wan_info.wan2:
        label_lines.append(
            _format_wan_interface_line(wan_info.wan2, "WAN2", is_dual=True, include_speed=True)
        )
        # Add IP from WAN1 for dual WAN display
        if wan_info.wan1 and wan_info.wan1.ip_address:
            label_lines.append(wan_info.wan1.ip_address)

    return label_lines


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


def _layout_nodeset(edges: list[Edge], node_types: dict[str, str]) -> set[str]:
    nodes = set(node_types.keys())
    for edge in edges:
        nodes.add(edge.left)
        nodes.add(edge.right)
    return nodes


def _build_children_maps(
    edges: list[Edge], nodes: set[str]
) -> tuple[dict[str, list[str]], dict[str, int]]:
    children: dict[str, list[str]] = {name: [] for name in nodes}
    incoming: dict[str, int] = {name: 0 for name in nodes}
    for edge in edges:
        children[edge.left].append(edge.right)
        incoming[edge.right] = incoming.get(edge.right, 0) + 1
    return children, incoming


def _sort_key_for_nodes(node_types: dict[str, str]) -> Callable[[str], tuple[int, str]]:
    type_order = {t: i for i, t in enumerate(_TYPE_ORDER)}

    def sort_key(name: str) -> tuple[int, str]:
        return (type_order.get(node_types.get(name, "other"), 99), name.lower())

    return sort_key


def _sort_children(children: dict[str, list[str]], sort_key) -> None:
    for _parent, child_list in children.items():
        child_list.sort(key=sort_key)


def _resolve_roots(
    nodes: set[str],
    incoming: dict[str, int],
    node_types: dict[str, str],
    sort_key,
) -> list[str]:
    gateways = [n for n, t in node_types.items() if t == "gateway"]
    roots = gateways if gateways else [n for n in nodes if incoming.get(n, 0) == 0]
    if not roots:
        roots = list(nodes)
    return sorted(roots, key=sort_key)


def _layout_positions(
    nodes: set[str],
    children: dict[str, list[str]],
    *,
    roots: list[str],
    sort_key,
) -> tuple[dict[str, float], dict[str, int]]:
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


def _tree_layout_indices(
    edges: list[Edge], node_types: dict[str, str]
) -> tuple[dict[str, float], dict[str, int]]:
    nodes = _layout_nodeset(edges, node_types)
    children, incoming = _build_children_maps(edges, nodes)
    sort_key = _sort_key_for_nodes(node_types)
    _sort_children(children, sort_key)
    roots = _resolve_roots(nodes, incoming, node_types, sort_key)
    return _layout_positions(nodes, children, roots=roots, sort_key=sort_key)


# --- Grouped layout functions ---


@dataclass(frozen=True)
class GroupBounds:
    name: str
    x: float
    y: float
    width: float
    height: float


def _assign_nodes_to_groups(
    nodes: set[str],
    groups: dict[str, list[str]],
) -> dict[str, str]:
    """Map each node to its group name."""
    node_to_group: dict[str, str] = {}
    for group_name, members in groups.items():
        for node in members:
            if node in nodes:
                node_to_group[node] = group_name
    return node_to_group


def _resolve_group_order(
    groups: dict[str, list[str]],
    group_order: list[str] | None,
) -> list[str]:
    """Return ordered list of group names."""
    if group_order:
        return [g for g in group_order if g in groups]
    return sorted(groups.keys())


def _filter_edges_for_group(
    edges: list[Edge],
    group_nodes: set[str],
) -> list[Edge]:
    """Return edges where both endpoints are in the group."""
    return [e for e in edges if e.left in group_nodes and e.right in group_nodes]


def _layout_single_group(
    edges: list[Edge],
    group_nodes: set[str],
    node_types: dict[str, str],
    options: SvgOptions,
) -> tuple[dict[str, tuple[float, float]], float, float]:
    """Layout nodes within a single group, return positions and dimensions."""
    group_edges = _filter_edges_for_group(edges, group_nodes)
    group_node_types = {n: node_types.get(n, "other") for n in group_nodes}
    positions, width, height = _layout_nodes(group_edges, group_node_types, options)
    return positions, float(width), float(height)


def _compute_group_bounds(
    group_name: str,
    positions: dict[str, tuple[float, float]],
    options: SvgOptions,
    offset_x: float,
) -> GroupBounds:
    """Compute bounding rectangle for a group."""
    if not positions:
        return GroupBounds(group_name, offset_x, 0, 100, 100)
    xs = [x for x, _ in positions.values()]
    ys = [y for _, y in positions.values()]
    min_x = min(xs) - options.group_padding
    min_y = min(ys) - options.group_padding
    max_x = max(xs) + options.node_width + options.group_padding
    max_y = max(ys) + options.node_height + options.group_padding
    return GroupBounds(group_name, min_x, min_y, max_x - min_x, max_y - min_y)


def _offset_positions(
    positions: dict[str, tuple[float, float]],
    dx: float,
    dy: float,
) -> dict[str, tuple[float, float]]:
    """Shift all positions by (dx, dy)."""
    return {name: (x + dx, y + dy) for name, (x, y) in positions.items()}


def _layout_grouped_nodes(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
    groups: dict[str, list[str]],
    group_order: list[str] | None,
) -> tuple[dict[str, tuple[float, float]], list[GroupBounds], int, int]:
    """Layout nodes in horizontal group lanes."""
    all_nodes = _layout_nodeset(edges, node_types)
    ordered_groups = _resolve_group_order(groups, group_order)
    node_to_group = _assign_nodes_to_groups(all_nodes, groups)

    all_positions: dict[str, tuple[float, float]] = {}
    group_bounds_list: list[GroupBounds] = []
    current_x = float(options.padding)
    max_height = 0.0

    for group_name in ordered_groups:
        group_nodes = set(groups.get(group_name, []))
        group_nodes = group_nodes & all_nodes
        if not group_nodes:
            continue
        positions, width, height = _layout_single_group(edges, group_nodes, node_types, options)
        offset_x = current_x - options.padding
        offset_positions = _offset_positions(positions, offset_x, 0)
        all_positions.update(offset_positions)
        bounds = _compute_group_bounds(group_name, offset_positions, options, current_x)
        group_bounds_list.append(bounds)
        current_x += width + options.group_gap
        max_height = max(max_height, height)

    ungrouped = all_nodes - set(node_to_group.keys())
    if ungrouped:
        ungrouped_positions, ug_width, ug_height = _layout_single_group(
            edges, ungrouped, node_types, options
        )
        offset_positions = _offset_positions(ungrouped_positions, current_x - options.padding, 0)
        all_positions.update(offset_positions)
        bounds = _compute_group_bounds("Other", offset_positions, options, current_x)
        group_bounds_list.append(bounds)
        current_x += ug_width + options.group_gap
        max_height = max(max_height, ug_height)

    total_width = int(current_x - options.group_gap + options.padding)
    total_height = int(max_height)
    return all_positions, group_bounds_list, total_width, total_height


def _render_group_boundaries(
    lines: list[str],
    group_bounds_list: list[GroupBounds],
    theme: SvgTheme,
    options: SvgOptions,
) -> None:
    """Render group background rectangles and labels."""
    label_size = options.font_size + 4
    for bounds in group_bounds_list:
        group_attr = _escape_attr(bounds.name, quote=True)
        fill, stroke = theme.group_colors(bounds.name)
        lines.append(f'<g class="network-group" data-group-name="{group_attr}">')
        lines.append(
            f'<rect class="group-boundary" x="{bounds.x}" y="{bounds.y}" '
            f'width="{bounds.width}" height="{bounds.height}" '
            f'rx="{theme.group_radius}" fill="{fill}" fill-opacity="0.3" '
            f'stroke="{stroke}" stroke-width="{theme.group_stroke_width}"/>'
        )
        label_x = bounds.x + 10
        label_y = bounds.y + label_size + 8
        lines.append(
            f'<text class="group-label" x="{label_x}" y="{label_y}" '
            f'fill="{stroke}" font-size="{label_size}" font-weight="bold">'
            f"{_escape_text(bounds.name.capitalize())}</text>"
        )
        lines.append("</g>")


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

    # Build label lines to calculate box size
    label_lines = _build_wan_label_lines(wan_info)

    # Calculate box dimensions based on content
    globe_size = 36
    padding = 10
    line_height = font_size + 4
    max_text_width = max((len(line) for line in label_lines), default=10) * font_size * 0.55
    box_width = max(globe_size + padding * 2, max_text_width + padding * 2)
    box_height = globe_size + len(label_lines) * line_height + padding * 3

    # Position box to the right of the gateway
    box_x = gx + options.node_width + 40
    box_y = gy + options.node_height / 2 - box_height / 2

    # Connection points
    gateway_connect_x = gx + options.node_width
    gateway_connect_y = gy + options.node_height / 2
    box_connect_x = box_x
    box_connect_y = box_y + box_height / 2

    lines.append('<g class="wan-upstream">')

    # Draw connector line from gateway to box
    lines.append(
        f'<path d="M {gateway_connect_x} {gateway_connect_y} '
        f'L {box_connect_x} {box_connect_y}" '
        f'stroke="#0288d1" stroke-width="2" fill="none" '
        f'stroke-linecap="round" opacity="0.8"/>'
    )

    # Draw bounding box with rounded corners
    lines.append(
        f'<rect x="{box_x}" y="{box_y}" width="{box_width}" height="{box_height}" '
        f'rx="6" ry="6" fill="{theme.background}" stroke="{theme.wan_globe[1]}" stroke-width="1.5"/>'
    )

    # Draw globe icon inline with gradient fill
    globe_cx = box_x + box_width / 2
    globe_cy = box_y + padding + globe_size / 2
    globe_r = globe_size / 2 - 2
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

    # Render label lines
    text_x = box_x + box_width / 2
    text_y = box_y + padding + globe_size + padding + font_size
    for i, label_text in enumerate(label_lines):
        y = text_y + i * line_height
        lines.append(
            f'<text x="{text_x}" y="{y}" text-anchor="middle" '
            f'fill="{theme.text_primary}" font-size="{font_size}">'
            f"{_escape_text(label_text)}</text>"
        )

    lines.append("</g>")


def render_svg(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    node_data: dict[str, dict[str, str]] | None = None,
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    wan_info: WanInfo | None = None,
) -> str:
    options = options or SvgOptions()
    icons = _load_icons(theme.icon_set)

    use_grouped = options.layout_mode == "grouped" and groups
    group_bounds_list: list[GroupBounds] = []
    if use_grouped and groups:
        positions, group_bounds_list, width, height = _layout_grouped_nodes(
            edges, node_types, options, groups, group_order
        )
    else:
        positions, width, height = _layout_nodes(edges, node_types, options)

    out_width = options.width or width
    out_height = options.height or height

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{out_width}" height="{out_height}" '
        f'viewBox="0 0 {width} {height}">',
        svg_defs("", theme),
        (
            "<style>text{font-family:Arial,Helvetica,sans-serif;font-size:"
            f"{options.font_size}px;"
            "}</style>"
        ),
        f'<rect width="100%" height="100%" fill="{theme.background}"/>',
    ]

    if use_grouped and group_bounds_list:
        _render_group_boundaries(lines, group_bounds_list, theme, options)

    node_port_labels, node_port_prefix = _render_svg_edges(
        lines, edges, positions, node_types, options, theme
    )
    _render_svg_nodes(
        lines,
        positions,
        node_types,
        node_port_labels,
        node_port_prefix,
        icons,
        options,
        node_data,
        theme,
        groups=groups,
    )

    # Render WAN upstream visualization
    if wan_info:
        # Find gateway position
        gateway_name = None
        for name, ntype in node_types.items():
            if ntype == "gateway":
                gateway_name = name
                break
        if gateway_name and gateway_name in positions:
            _render_wan_upstream(lines, wan_info, positions[gateway_name], options, theme)

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


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
        src_x, src_y = positions[edge.left]
        dst_x, dst_y = positions[edge.right]
        src_cx = src_x + options.node_width / 2
        dst_cx = dst_x + options.node_width / 2
        src_bottom = src_y + options.node_height
        dst_top = dst_y
        mid_y = (src_bottom + dst_top) / 2
        width_px = 2 if edge.poe else 1
        if math.isclose(src_cx, dst_cx, abs_tol=0.01):
            elbow_x = src_cx + 0.5
            path = (
                f"M {src_cx} {src_bottom} L {src_cx} {mid_y} "
                f"L {elbow_x} {mid_y} L {dst_cx} {mid_y} L {dst_cx} {dst_top}"
            )
        else:
            path = (
                f"M {src_cx} {src_bottom} L {src_cx} {mid_y} "
                f"L {dst_cx} {mid_y} L {dst_cx} {dst_top}"
            )
        left_attr = _escape_attr(edge.left, quote=True)
        right_attr = _escape_attr(edge.right, quote=True)
        vlan_attrs = _vlan_data_attrs(edge)
        base_attrs = f'data-edge-left="{left_attr}" data-edge-right="{right_attr}"'
        if vlan_attrs:
            base_attrs = f"{base_attrs} {vlan_attrs}"

        # Determine VLANs to visualize (active only, with optional limit)
        display_vlans = edge.active_vlans
        if max_vlan_colors and len(display_vlans) > max_vlan_colors:
            display_vlans = display_vlans[:max_vlan_colors]

        # Client edges are semi-transparent to reduce visual clutter
        opacity = _edge_opacity(node_types, edge)
        opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

        if display_vlans:
            # Render striped VLAN edge
            _render_vlan_striped_edge(
                lines, path, display_vlans, theme, width_px, edge.wireless, base_attrs, opacity
            )
            # Render VLAN endpoint markers at destination
            _render_vlan_endpoint_markers(lines, dst_cx, dst_top + 4, display_vlans, theme)
        else:
            # Render standard edge (no VLAN info or no active VLANs)
            color = "url(#link-poe)" if edge.poe else "url(#link-standard)"
            dash = ' stroke-dasharray="6 4"' if edge.wireless else ""
            lines.append(
                f'<path d="{path}" stroke="{color}" stroke-width="{width_px}" '
                f'fill="none"{dash}{opacity_attr} {base_attrs}/>'
            )
        if edge.poe:
            icon_x = dst_cx
            icon_y = dst_top - 6
            lines.append(
                f'<text x="{icon_x}" y="{icon_y}" text-anchor="middle" fill="#1e88e5" '
                f'font-size="{max(options.font_size, 10)}">⚡</text>'
            )
    return node_port_labels, node_port_prefix


def _record_edge_labels(
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
            upstream_name = _extract_device_name(upstream_part) or upstream_node
            node_port_labels.setdefault(client_node, f"{upstream_name}: {port_text}")
            node_port_prefix.setdefault(client_node, upstream_name)
        return
    upstream_part = edge.label.split("<->", 1)[0].strip()
    upstream_name = _extract_device_name(upstream_part) or edge.left
    if label_text.lower().startswith("port "):
        label_text = f"{upstream_name} {label_text}"
    node_port_labels.setdefault(edge.right, label_text)
    node_port_prefix.setdefault(edge.right, upstream_name)


def _render_svg_nodes(
    lines: list[str],
    positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    node_port_labels: dict[str, str],
    node_port_prefix: dict[str, str],
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
            f'<text x="{text_x}" y="{text_y}" fill="{theme.text_primary}" '
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
    rendered = [f' {key}="{_escape_attr(value, quote=True)}"' for key, value in attrs.items()]
    return "".join(rendered)


def _iso_project(layout: IsoLayout, gx: float, gy: float) -> tuple[float, float]:
    iso_x = (gx - gy) * (layout.step_width / 2)
    iso_y = (gx + gy) * (layout.step_height / 2)
    return iso_x, iso_y


def _iso_project_center(layout: IsoLayout, gx: float, gy: float) -> tuple[float, float]:
    return _iso_project(layout, gx + 0.5, gy + 0.5)


def _iso_layout_positions(
    edges: list[Edge],
    node_types: dict[str, str],
    options: SvgOptions,
) -> IsoLayoutPositions:
    layout = _iso_layout(options)
    positions_index, levels = _tree_layout_indices(edges, node_types)
    grid_positions: dict[str, tuple[float, float]] = {}
    positions: dict[str, tuple[float, float]] = {}
    for name, idx in positions_index.items():
        level = levels.get(name, 0)
        gx = round(idx * layout.grid_spacing_x)
        gy = round(float(level) * layout.grid_spacing_y)
        grid_positions[name] = (float(gx), float(gy))
        iso_x, iso_y = _iso_project_center(layout, float(gx), float(gy))
        positions[name] = (iso_x, iso_y)
    if positions:
        min_x = min(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        max_x = max(x for x, _ in positions.values())
        max_y = max(y for _, y in positions.values())
    else:
        min_x = min_y = 0.0
        max_x = max_y = 0.0
    # Extra padding for west/northwest to prevent clipping
    nw_pad = 300
    offset_x = -min_x + layout.padding + nw_pad
    offset_y = -min_y + layout.padding + layout.tile_y_offset + nw_pad
    for name, (x, y) in positions.items():
        positions[name] = (x + offset_x, y + offset_y)
    # Expand viewport to show more of the grid
    viewport_expand = 400
    width = (
        max_x
        - min_x
        + layout.tile_width
        + layout.padding * 2
        + layout.extra_pad
        + viewport_expand
        + nw_pad
    )
    height = (
        max_y
        - min_y
        + layout.tile_height
        + layout.padding * 2
        + layout.tile_y_offset
        + layout.extra_pad
        + viewport_expand
        + nw_pad
    )
    return IsoLayoutPositions(
        layout=layout,
        grid_positions=grid_positions,
        positions=positions,
        width=width,
        height=height,
        offset_x=offset_x,
        offset_y=offset_y,
    )


def _iso_grid_lines(
    grid_positions: dict[str, tuple[float, float]],
    layout: IsoLayout,
) -> list[str]:
    if not grid_positions:
        return []
    min_gx = min(gx for gx, _ in grid_positions.values())
    max_gx = max(gx for gx, _ in grid_positions.values())
    min_gy = min(gy for _, gy in grid_positions.values())
    max_gy = max(gy for _, gy in grid_positions.values())
    pad = 36  # Large grid extent for visual appeal
    gx_start = int(math.floor(min_gx)) - pad
    gx_end = int(math.ceil(max_gx)) + pad
    gy_start = int(math.floor(min_gy)) - pad
    gy_end = int(math.ceil(max_gy)) + pad
    grid_lines: list[str] = []
    for gx in range(gx_start, gx_end + 1):
        x1, y1 = _iso_project(layout, float(gx), float(gy_start))
        x2, y2 = _iso_project(layout, float(gx), float(gy_end))
        x1 += layout.padding
        y1 += layout.padding
        x2 += layout.padding
        y2 += layout.padding
        grid_lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#efefef" stroke-width="0.6"/>'
        )
    for gy in range(gy_start, gy_end + 1):
        x1, y1 = _iso_project(layout, float(gx_start), float(gy))
        x2, y2 = _iso_project(layout, float(gx_end), float(gy))
        x1 += layout.padding
        y1 += layout.padding
        x2 += layout.padding
        y2 += layout.padding
        grid_lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#efefef" stroke-width="0.6"/>'
        )
    return grid_lines


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


def _render_iso_edges(
    lines: list[str],
    edges: list[Edge],
    *,
    positions: dict[str, tuple[float, float]],
    grid_positions: dict[str, tuple[float, float]],
    node_types: dict[str, str],
    layout: IsoLayout,
    options: SvgOptions,
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
        src_grid = grid_positions.get(edge.left)
        dst_grid = grid_positions.get(edge.right)
        if not src_grid or not dst_grid:
            continue
        width_px = 5 if edge.poe else 4
        src_gx, src_gy = float(src_grid[0]), float(src_grid[1])
        dst_gx, dst_gy = float(dst_grid[0]), float(dst_grid[1])
        src_cx, src_cy = _iso_front_anchor(
            layout, gx=src_gx, gy=src_gy, offset_x=offset_x, offset_y=offset_y
        )
        dst_cx, dst_cy = _iso_front_anchor(
            layout, gx=dst_gx, gy=dst_gy, offset_x=offset_x, offset_y=offset_y
        )
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
        left_attr = _escape_attr(edge.left, quote=True)
        right_attr = _escape_attr(edge.right, quote=True)
        vlan_attrs = _vlan_data_attrs(edge)
        base_attrs = f'data-edge-left="{left_attr}" data-edge-right="{right_attr}"'
        if vlan_attrs:
            base_attrs = f"{base_attrs} {vlan_attrs}"

        # Determine VLANs to visualize
        display_vlans = edge.active_vlans
        if max_vlan_colors and len(display_vlans) > max_vlan_colors:
            display_vlans = display_vlans[:max_vlan_colors]

        # Client edges are semi-transparent to reduce visual clutter
        opacity = _edge_opacity(node_types, edge)
        opacity_attr = f' opacity="{opacity}"' if opacity < 1.0 else ""

        if display_vlans:
            _render_iso_vlan_striped_edge(
                lines, path, display_vlans, theme, width_px, edge.wireless, base_attrs, opacity
            )
            # Render VLAN endpoint markers at destination
            marker_x = dst_cx + layout.tile_width * 0.3
            marker_y = dst_cy - layout.tile_height * 0.2
            _render_vlan_endpoint_markers(lines, marker_x, marker_y, display_vlans, theme)
        else:
            color = "url(#iso-link-poe)" if edge.poe else "url(#iso-link-standard)"
            dash = ' stroke-dasharray="8 6"' if edge.wireless else ""
            lines.append(
                f'<path d="{path}" stroke="{color}" stroke-width="{width_px}" '
                f'fill="none" stroke-linecap="round" stroke-linejoin="round"{dash}{opacity_attr} '
                f"{base_attrs}/>"
            )
        if edge.poe:
            icon_x = dst_cx
            icon_y = dst_cy - layout.tile_height * 0.4
            lines.append(
                f'<text x="{icon_x}" y="{icon_y}" text-anchor="middle" fill="#1e88e5" '
                f'font-size="{max(options.font_size, 10)}">⚡</text>'
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
    node_port_labels.setdefault(edge.right, label_text)
    node_port_prefix.setdefault(edge.right, _shorten_prefix(edge.left))


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
    node_type: str,
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
        node_type=node_type,
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
            fill="#555",
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
    label_x = center_x + tile_height * 0.05
    label_y = center_y + font_size * 0.5 + 2  # Centered vertically on the face

    return label_x, label_y, angle


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
    left_fill = "#d0d0d0" if node_type == "other" else "#dcdcdc"
    right_fill = "#c2c2c2" if node_type == "other" else "#c8c8c8"
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
    icon_href = icons.get(node_type, icons.get("other"))
    center_x = x + tile_w / 2
    center_y = y + tile_h / 2
    icon_center_x = center_x
    icon_center_y = center_y
    iso_icon_size = min(tile_w, tile_h) * 1.26
    if port_label:
        font_size = max(options.font_size - 2, 8)
        prefix = port_prefix or "switch"
        icon_center_x, icon_center_y = _render_iso_port_label(
            lines,
            port_label=port_label,
            node_type=node_type,
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
            f'preserveAspectRatio="xMidYMid meet"/>'
        )

    # Position name label
    name_font_size = max(options.font_size - 2, 8)
    if not port_label and node_depth > 0:
        # Nodes without port labels: render name on front (left) face
        name_x, name_y, name_angle = _iso_front_face_label_position(
            left,
            tile_height=tile_h,
            font_size=name_font_size,
        )
    else:
        # Nodes with port labels: render name on bottom edge of top face
        name_x, name_y, name_angle = _iso_name_label_position(
            top,
            tile_width=tile_w,
            tile_height=tile_h,
            font_size=name_font_size,
        )

    name_transform = (
        f"translate({name_x} {name_y}) rotate({name_angle}) skewX(30) "
        f"translate({-name_x} {-name_y})"
    )
    lines.append(
        f'<text x="{name_x}" y="{name_y}" text-anchor="middle" fill="{theme.text_primary}" '
        f'font-size="{name_font_size}" transform="{name_transform}">{_escape_text(name)}</text>'
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


def _render_iso_wan_upstream(
    lines: list[str],
    wan_info: WanInfo,
    gateway_position: tuple[float, float],
    layout: IsoLayout,
    options: SvgOptions,
    theme: SvgTheme,
) -> None:
    """Render WAN upstream visualization (isometric view)."""
    gx, gy = gateway_position
    tile_w = layout.tile_width
    tile_h = layout.tile_height

    # Build label lines to calculate box size
    label_lines = _build_wan_label_lines(wan_info)
    font_size = max(options.font_size - 1, 8)

    # Calculate box dimensions based on content
    globe_size = 40
    padding = 12
    line_height = font_size + 4
    max_text_width = max((len(line) for line in label_lines), default=10) * font_size * 0.55
    box_width = max(globe_size + padding * 2, max_text_width + padding * 2)
    box_height = globe_size + len(label_lines) * line_height + padding * 3

    # Position box to the east (right side) of the gateway
    # Move along the isometric NE direction
    box_x = gx + tile_w + 60
    box_y = gy - tile_h / 2 - box_height / 2 + 20

    # Connection point on gateway (east edge of tile)
    gateway_connect_x = gx + tile_w * 0.75
    gateway_connect_y = gy + tile_h * 0.25

    # Connection point on box (left edge, middle)
    box_connect_x = box_x
    box_connect_y = box_y + box_height / 2

    lines.append('<g class="wan-upstream">')

    # Draw connector line from gateway to box
    lines.append(
        f'<path d="M {gateway_connect_x} {gateway_connect_y} '
        f'L {box_connect_x} {box_connect_y}" '
        f'stroke="#0288d1" stroke-width="3" fill="none" '
        f'stroke-linecap="round" opacity="0.8"/>'
    )

    # Draw bounding box with rounded corners
    lines.append(
        f'<rect x="{box_x}" y="{box_y}" width="{box_width}" height="{box_height}" '
        f'rx="8" ry="8" fill="{theme.background}" stroke="{theme.wan_globe[1]}" stroke-width="2"/>'
    )

    # Draw globe icon inline with gradient fill
    globe_cx = box_x + box_width / 2
    globe_cy = box_y + padding + globe_size / 2
    globe_r = globe_size / 2 - 2
    lines.append(f'<g transform="translate({globe_cx}, {globe_cy})">')
    # Globe circle
    lines.append(
        f'<circle cx="0" cy="0" r="{globe_r}" fill="none" '
        f'stroke="url(#iso-globe)" stroke-width="2"/>'
    )
    # Vertical ellipse (meridian)
    lines.append(
        f'<ellipse cx="0" cy="0" rx="{globe_r * 0.35}" ry="{globe_r}" '
        f'fill="none" stroke="url(#iso-globe)" stroke-width="1.5"/>'
    )
    # Horizontal line (equator)
    lines.append(
        f'<line x1="{-globe_r}" y1="0" x2="{globe_r}" y2="0" '
        f'stroke="url(#iso-globe)" stroke-width="1.5"/>'
    )
    # Latitude lines
    lines.append(
        f'<ellipse cx="0" cy="{-globe_r * 0.5}" rx="{globe_r * 0.87}" ry="{globe_r * 0.2}" '
        f'fill="none" stroke="url(#iso-globe)" stroke-width="1"/>'
    )
    lines.append(
        f'<ellipse cx="0" cy="{globe_r * 0.5}" rx="{globe_r * 0.87}" ry="{globe_r * 0.2}" '
        f'fill="none" stroke="url(#iso-globe)" stroke-width="1"/>'
    )
    lines.append("</g>")

    # Render label lines
    text_x = box_x + box_width / 2
    text_y = box_y + padding + globe_size + padding + font_size
    for i, label_text in enumerate(label_lines):
        y = text_y + i * line_height
        lines.append(
            f'<text x="{text_x}" y="{y}" text-anchor="middle" '
            f'fill="{theme.text_primary}" font-size="{font_size}">'
            f"{_escape_text(label_text)}</text>"
        )

    lines.append("</g>")


@dataclass(frozen=True)
class IsoGroupBounds:
    name: str
    points: list[tuple[float, float]]  # 4 corners of the parallelogram
    label_x: float
    label_y: float


def _compute_iso_group_bounds(
    grid_positions: dict[str, tuple[float, float]],
    groups: dict[str, list[str]],
    group_order: list[str] | None,
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    options: SvgOptions,
) -> list[IsoGroupBounds]:
    """Compute isometric group bounds as parallelograms aligned with grid."""
    ordered_groups = _resolve_group_order(groups, group_order)
    node_to_group = _build_node_to_group_map(groups)
    bounds_list: list[IsoGroupBounds] = []
    # Convert screen padding to grid units
    padding = options.group_padding / layout.step_width + 0.5

    for group_name in ordered_groups:
        group_grid = {
            n: pos for n, pos in grid_positions.items() if node_to_group.get(n) == group_name
        }
        if not group_grid:
            continue
        bounds = _iso_group_parallelogram(
            group_name, group_grid, layout, offset_x, offset_y, padding
        )
        bounds_list.append(bounds)
    return bounds_list


def _iso_group_parallelogram(
    name: str,
    group_grid: dict[str, tuple[float, float]],
    layout: IsoLayout,
    offset_x: float,
    offset_y: float,
    padding: float,
) -> IsoGroupBounds:
    """Create isometric parallelogram bounds from grid positions."""
    gxs = [gx for gx, _ in group_grid.values()]
    gys = [gy for _, gy in group_grid.values()]

    is_single_node = len(group_grid) == 1
    if is_single_node:
        # For single-node groups: boundary centered around the node
        # Shift to align with node's visual center
        node_half = 0.8  # Half-size of boundary in grid units
        center_gx = min(gxs) + 1.45  # Tuned for visual centering
        center_gy = min(gys) + 0.45
        min_gx = center_gx - node_half
        max_gx = center_gx + node_half
        min_gy = center_gy - node_half
        max_gy = center_gy + node_half
    else:
        # For multi-node groups: use grid spacing with padding
        min_gx = min(gxs) - padding
        max_gx = max(gxs) + layout.grid_spacing_x + padding
        min_gy = min(gys) - padding
        max_gy = max(gys) + layout.grid_spacing_y + padding

    # Project grid corners to screen coordinates
    corners_grid = [
        (min_gx, min_gy),  # top
        (max_gx, min_gy),  # right
        (max_gx, max_gy),  # bottom
        (min_gx, max_gy),  # left
    ]
    points = [
        (
            _iso_project(layout, gx, gy)[0] + offset_x,
            _iso_project(layout, gx, gy)[1] + offset_y,
        )
        for gx, gy in corners_grid
    ]

    # Position label at the top corner, offset inward along the right edge
    top_x, top_y = points[0]
    right_x, right_y = points[1]
    label_x = top_x + (right_x - top_x) * 0.15 - 30  # Shifted NW
    label_y = top_y + (right_y - top_y) * 0.15 - 20
    return IsoGroupBounds(name=name, points=points, label_x=label_x, label_y=label_y)


def _render_iso_group_boundaries(
    lines: list[str],
    bounds_list: list[IsoGroupBounds],
    theme: SvgTheme,
    font_size: int = 10,
) -> None:
    """Render isometric group boundaries as parallelograms."""
    label_size = 48  # Labels
    iso_angle = 30  # Match isometric perspective
    for bounds in bounds_list:
        group_attr = _escape_attr(bounds.name, quote=True)
        fill, stroke = theme.group_colors(bounds.name)
        points_str = " ".join(f"{x},{y}" for x, y in bounds.points)
        lines.append(f'<g class="network-group" data-group-name="{group_attr}">')
        lines.append(
            f'<polygon class="group-boundary" points="{points_str}" '
            f'fill="{fill}" fill-opacity="0.35" '
            f'stroke="{stroke}" stroke-width="{theme.group_stroke_width}"/>'
        )
        label_text = _escape_text(bounds.name.capitalize())
        lx, ly = bounds.label_x, bounds.label_y
        # Isometric transform: rotate + skew to follow 30° perspective
        label_transform = (
            f"translate({lx} {ly}) rotate({iso_angle}) skewX({iso_angle}) translate({-lx} {-ly})"
        )
        # Text with thin outline for readability
        lines.append(
            f'<text class="group-label" x="{lx}" y="{ly}" '
            f'font-size="{label_size}" font-weight="bold" fill="{stroke}" '
            f'stroke="#ffffff" stroke-width="2" paint-order="stroke fill" '
            f'opacity="0.7" transform="{label_transform}">'
            f"{label_text}</text>"
        )
        lines.append("</g>")


def render_svg_isometric(
    edges: list[Edge],
    *,
    node_types: dict[str, str],
    options: SvgOptions | None = None,
    theme: SvgTheme = DEFAULT_THEME,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    wan_info: WanInfo | None = None,
) -> str:
    options = options or SvgOptions()
    icons = _load_isometric_icons(theme.icon_set, theme.icon_decal)
    layout_positions = _iso_layout_positions(edges, node_types, options)
    layout = layout_positions.layout
    grid_positions = layout_positions.grid_positions
    positions = layout_positions.positions

    out_width = options.width or int(layout_positions.width)
    out_height = options.height or int(layout_positions.height)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{out_width}" height="{out_height}" '
        f'viewBox="0 0 {layout_positions.width} {layout_positions.height}">',
        svg_defs("iso", theme),
        (
            "<style>text{font-family:Arial,Helvetica,sans-serif;}"
            f"text:not(.group-label){{font-size:{options.font_size}px;}}"
            "</style>"
        ),
        f'<rect width="100%" height="100%" fill="{theme.background}"/>',
    ]

    use_grouped = options.layout_mode == "grouped" and groups
    if use_grouped and groups:
        group_bounds_list = _compute_iso_group_bounds(
            grid_positions,
            groups,
            group_order,
            layout,
            layout_positions.offset_x,
            layout_positions.offset_y,
            options,
        )
        _render_iso_group_boundaries(lines, group_bounds_list, theme, options.font_size)

    grid_lines = _iso_grid_lines(grid_positions, layout)
    if grid_lines:
        lines.append('<g class="iso-grid" opacity="0.7">')
        lines.extend(grid_lines)
        lines.append("</g>")

    node_port_labels: dict[str, str] = {}
    node_port_prefix: dict[str, str] = {}
    _render_iso_edges(
        lines,
        edges,
        positions=positions,
        grid_positions=grid_positions,
        node_types=node_types,
        layout=layout,
        options=options,
        theme=theme,
        offset_x=layout_positions.offset_x,
        offset_y=layout_positions.offset_y,
        node_port_labels=node_port_labels,
        node_port_prefix=node_port_prefix,
    )
    _render_iso_nodes(
        lines,
        positions=positions,
        node_types=node_types,
        icons=icons,
        options=options,
        layout=layout,
        node_port_labels=node_port_labels,
        node_port_prefix=node_port_prefix,
        theme=theme,
    )

    # Render WAN upstream visualization
    if wan_info:
        # Find gateway position
        gateway_name = None
        for name, ntype in node_types.items():
            if ntype == "gateway":
                gateway_name = name
                break
        if gateway_name and gateway_name in positions:
            _render_iso_wan_upstream(
                lines, wan_info, positions[gateway_name], layout, options, theme
            )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"
