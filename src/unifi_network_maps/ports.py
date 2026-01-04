"""Port parsing helpers shared across modules."""

from __future__ import annotations

import re


def extract_port_number(label: str | None) -> int | None:
    if not label:
        return None
    # Matches: "Port 3", "eth1"; non-matches: "wan", "portX".
    match = re.search(r"(?:^|[^0-9])(?:port|eth)\s*([0-9]+)", label.strip(), re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def normalize_port_label(label: str) -> str:
    trimmed = label.strip()
    number = extract_port_number(trimmed)
    if number is not None:
        return f"Port {number}"
    return trimmed
