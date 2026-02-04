"""Shared low-level helpers for the model layer.

These tiny pure functions are used across multiple model modules.
Centralising them here avoids circular-import issues and duplication.
"""

from __future__ import annotations

from collections.abc import Iterable


def as_list(value: object | None) -> list[object]:
    """Coerce *value* to a list, handling dicts, iterables, and None."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str | bytes):
        return []
    if isinstance(value, Iterable):
        return list(value)
    return []


def as_bool(value: object | None) -> bool:
    """Coerce *value* to a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def first_attr(obj: object, *names: str) -> object | None:
    """Return the first non-None field value from *names*."""
    for name in names:
        value = get_field(obj, name)
        if value is not None:
            return value
    return None


def first_string_field(obj: object, *keys: str) -> str | None:
    """Return the first non-empty stripped string from *keys*."""
    for key in keys:
        value = get_field(obj, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def normalize_mac(value: str) -> str:
    return value.strip().lower()


def get_field(obj: object, name: str) -> object | None:
    """Read a named field from a dict **or** an attribute-style object."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
