"""Markdown table helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable


def markdown_table_lines(
    headers: list[str],
    rows: Iterable[Iterable[str]],
    *,
    escape: Callable[[str], str] | None = None,
) -> list[str]:
    esc = escape or (lambda value: value)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(esc(cell) for cell in row) + " |")
    return lines
