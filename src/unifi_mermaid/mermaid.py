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


def _build_id_map(edges: Iterable[Edge]) -> dict[str, str]:
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

    for edge in edges:
        assign(edge.left)
        assign(edge.right)

    return id_map


def _node_ref(name: str, node_id: str) -> str:
    return f'{node_id}["{_escape(name)}"]'


def render_mermaid(edges: Iterable[Edge], direction: str = "LR") -> str:
    edge_list = list(edges)
    id_map = _build_id_map(edge_list)
    lines = [f"graph {direction}"]
    for edge in edge_list:
        left = _node_ref(edge.left, id_map[edge.left])
        right = _node_ref(edge.right, id_map[edge.right])
        if edge.label:
            label = _escape(edge.label)
            lines.append(f'  {left} ---|"{label}"| {right}')
        else:
            lines.append(f"  {left} --- {right}")
    return "\n".join(lines) + "\n"
