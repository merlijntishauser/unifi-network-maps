"""Edge label helpers."""

from __future__ import annotations


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
