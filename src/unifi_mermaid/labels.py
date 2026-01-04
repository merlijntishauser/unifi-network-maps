"""Edge label helpers."""

from __future__ import annotations

from collections.abc import Callable


def compose_port_label(left: str, right: str, port_map: dict[tuple[str, str], str]) -> str | None:
    left_label = port_map.get((left, right))
    right_label = port_map.get((right, left))
    if left_label and right_label:
        return f"{left}: {left_label} <-> {right}: {right_label}"
    if left_label:
        return f"{left}: {left_label} <-> {right}: ?"
    if right_label:
        return f"{left}: ? <-> {right}: {right_label}"
    return None


def order_edge_names(
    left: str,
    right: str,
    port_map: dict[tuple[str, str], str],
    rank_for_name: Callable[[str], int],
) -> tuple[str, str]:
    left_label = port_map.get((left, right))
    right_label = port_map.get((right, left))
    if left_label is None and right_label is not None:
        return (right, left)
    if left_label and right_label:
        left_rank = rank_for_name(left)
        right_rank = rank_for_name(right)
        if (left_rank, left.lower()) > (right_rank, right.lower()):
            return (right, left)
    return (left, right)
