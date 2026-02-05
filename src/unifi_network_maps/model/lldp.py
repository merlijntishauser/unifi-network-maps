"""LLDP parsing and port label helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .ports import extract_port_number, normalize_port_label


@dataclass(frozen=True)
class LLDPEntry:
    chassis_id: str
    port_id: str
    port_desc: str | None = None
    local_port_name: str | None = None
    local_port_idx: int | None = None


def _get_field(entry: object, *names: str) -> str | int | None:
    """Get a field by trying multiple names (snake_case and camelCase variants)."""
    if isinstance(entry, dict):
        for name in names:
            val = entry.get(name)
            if val is not None:
                return val  # type: ignore[return-value]
    else:
        for name in names:
            val = getattr(entry, name, None)
            if val is not None:
                return val  # type: ignore[return-value]
    return None


def coerce_lldp(entry: object) -> LLDPEntry:
    chassis_id = _get_field(entry, "chassis_id", "chassisId")
    port_id = _get_field(entry, "port_id", "portId")
    port_desc = _get_field(entry, "port_desc", "portDesc", "port_descr", "portDescr")
    local_port_name = _get_field(entry, "local_port_name", "localPortName")
    local_port_idx = _get_field(entry, "local_port_idx", "localPortIdx")

    if not chassis_id or not port_id:
        raise ValueError("LLDP entry missing chassis_id or port_id")
    return LLDPEntry(
        chassis_id=str(chassis_id),
        port_id=str(port_id),
        port_desc=str(port_desc) if port_desc else None,
        local_port_name=str(local_port_name) if local_port_name else None,
        local_port_idx=int(local_port_idx) if local_port_idx is not None else None,
    )


def _looks_like_mac(value: str | None) -> bool:
    if not value:
        return False
    cleaned = value.strip().lower()
    if cleaned.count(":") == 5:
        return all(
            len(part) == 2 and all(ch in "0123456789abcdef" for ch in part)
            for part in cleaned.split(":")
        )
    return False


def _port_label_parts(entry: LLDPEntry) -> tuple[int | None, str | None, str | None]:
    number = entry.local_port_idx
    name = normalize_port_label(entry.local_port_name) if entry.local_port_name else None
    desc = (
        entry.port_desc.strip()
        if entry.port_desc and not _looks_like_mac(entry.port_desc)
        else None
    )

    if entry.port_id and not _looks_like_mac(entry.port_id) and name is None:
        name = normalize_port_label(entry.port_id)

    if number is None:
        number = extract_port_number(name)
    if number is None:
        number = extract_port_number(desc)

    return number, name, desc


def local_port_label(entry: LLDPEntry) -> str | None:
    number, name, desc = _port_label_parts(entry)
    if number is not None and desc:
        return f"Port {number} ({desc})"
    if number is not None:
        return f"Port {number}"
    if name:
        return name
    if desc:
        return desc
    return None
