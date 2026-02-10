"""Layout algorithms for orthogonal SVG network diagrams."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from html import escape as _escape_html

from ..model.topology import Edge
from .svg_icons import _TYPE_ORDER
from .svg_theme import SvgOptions


@dataclass(frozen=True)
class GroupBounds:
    name: str
    x: float
    y: float
    width: float
    height: float


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
