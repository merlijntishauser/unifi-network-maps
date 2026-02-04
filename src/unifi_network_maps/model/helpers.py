"""Shared low-level helpers for the model layer.

These tiny pure functions are used across multiple model modules.
Centralising them here avoids circular-import issues and duplication.
"""

from __future__ import annotations


def normalize_mac(value: str) -> str:
    return value.strip().lower()


def get_field(obj: object, name: str) -> object | None:
    """Read a named field from a dict **or** an attribute-style object."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
