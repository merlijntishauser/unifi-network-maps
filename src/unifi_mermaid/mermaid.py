"""Mermaid diagram rendering."""

from __future__ import annotations

from typing import Iterable

from .topology import Edge


def _escape(label: str) -> str:
    return label.replace('"', '\\"')


def render_mermaid(edges: Iterable[Edge], direction: str = "LR") -> str:
    lines = [f"graph {direction}"]
    for edge in edges:
        left = _escape(edge.left)
        right = _escape(edge.right)
        if edge.label:
            label = _escape(edge.label)
            lines.append(f"  \"{left}\" ---|\"{label}\"| \"{right}\"")
        else:
            lines.append(f"  \"{left}\" --- \"{right}\"")
    return "\n".join(lines) + "\n"
