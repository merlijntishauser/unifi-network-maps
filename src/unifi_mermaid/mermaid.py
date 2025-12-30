"""Mermaid diagram rendering."""

from __future__ import annotations

from collections.abc import Iterable

from .topology import Edge


def _escape(label: str) -> str:
    return label.replace('"', '\\"')


def _slugify(value: str) -> str:
    normalized = []
    for ch in value.strip():
        if ch.isalnum():
            normalized.append(ch.lower())
        else:
            normalized.append("_")
    slug = "".join(normalized).strip("_")
    if not slug or slug[0].isdigit():
        slug = f"n_{slug}" if slug else "n"
    return slug


def _build_id_map(edges: Iterable[Edge], nodes: Iterable[str]) -> dict[str, str]:
    id_map: dict[str, str] = {}
    used: set[str] = set()

    def assign(name: str) -> None:
        if name in id_map:
            return
        base = _slugify(name)
        candidate = base
        counter = 2
        while candidate in used:
            candidate = f"{base}_{counter}"
            counter += 1
        id_map[name] = candidate
        used.add(candidate)

    for node in nodes:
        assign(node)
    for edge in edges:
        assign(edge.left)
        assign(edge.right)

    return id_map


def _node_ref(name: str, node_id: str) -> str:
    return f'{node_id}["{_escape(name)}"]'


def render_mermaid(
    edges: Iterable[Edge],
    direction: str = "LR",
    *,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    rank_edges: list[tuple[str, str]] | None = None,
) -> str:
    edge_list = list(edges)
    group_nodes: list[str] = []
    if groups:
        for members in groups.values():
            group_nodes.extend(members)
    id_map = _build_id_map(edge_list, group_nodes)
    lines = [f"graph {direction}"]
    if groups:
        ordered = group_order or list(groups.keys())
        for group_name in ordered:
            members = groups.get(group_name, [])
            if not members:
                continue
            group_id = _slugify(f"group_{group_name}")
            label = group_name.replace("_", " ").title()
            lines.append(f'  subgraph {group_id}["{_escape(label)}"]')
            for member in members:
                lines.append(f"    {_node_ref(member, id_map[member])}")
            lines.append("  end")
    use_node_labels = not groups
    link_styles: list[int] = []
    link_index = 0
    for edge in edge_list:
        if use_node_labels:
            left = _node_ref(edge.left, id_map[edge.left])
            right = _node_ref(edge.right, id_map[edge.right])
        else:
            left = id_map[edge.left]
            right = id_map[edge.right]
        if edge.label:
            label = _escape(edge.label)
            lines.append(f'  {left} ---|"{label}"| {right}')
        else:
            lines.append(f"  {left} --- {right}")
        link_index += 1

    if rank_edges:
        for left_name, right_name in rank_edges:
            left_id = id_map.get(left_name)
            right_id = id_map.get(right_name)
            if not left_id or not right_id:
                continue
            lines.append(f"  {left_id} --- {right_id}")
            link_styles.append(link_index)
            link_index += 1

    for index in link_styles:
        lines.append(f"  linkStyle {index} stroke:transparent,stroke-width:0px")
    return "\n".join(lines) + "\n"
