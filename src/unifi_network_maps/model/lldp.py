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


def coerce_lldp(entry: object) -> LLDPEntry:
    if isinstance(entry, dict):
        chassis_id = entry.get("chassis_id") or entry.get("chassisId")
        port_id = entry.get("port_id") or entry.get("portId")
        port_desc = (
            entry.get("port_desc")
            or entry.get("portDesc")
            or entry.get("port_descr")
            or entry.get("portDescr")
        )
        local_port_name = entry.get("local_port_name") or entry.get("localPortName")
        local_port_idx = entry.get("local_port_idx") or entry.get("localPortIdx")
    else:
        chassis_id = getattr(entry, "chassis_id", None) or getattr(entry, "chassisId", None)
        port_id = getattr(entry, "port_id", None) or getattr(entry, "portId", None)
        port_desc = (
            getattr(entry, "port_desc", None)
            or getattr(entry, "portDesc", None)
            or getattr(entry, "port_descr", None)
            or getattr(entry, "portDescr", None)
        )
        local_port_name = getattr(entry, "local_port_name", None) or getattr(
            entry, "localPortName", None
        )
        local_port_idx = getattr(entry, "local_port_idx", None) or getattr(
            entry, "localPortIdx", None
        )
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
