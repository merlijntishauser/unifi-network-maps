"""VLAN inventory helpers."""

from __future__ import annotations

from collections.abc import Iterable


def _as_list(value: object | None) -> list[object]:
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


def _get_attr(obj: object, name: str) -> object | None:
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _first_attr(obj: object, *names: str) -> object | None:
    for name in names:
        value = _get_attr(obj, name)
        if value is not None:
            return value
    return None


def _as_bool(value: object | None) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _as_vlan_id(value: object | None) -> int | None:
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        return int(value) if value.isdigit() and int(value) > 0 else None
    return None


def _network_vlan_id(network: object) -> int | None:
    vlan_value = _first_attr(network, "vlan", "vlan_id", "vlanId", "vlanid")
    vlan_enabled = _as_bool(_first_attr(network, "vlan_enabled", "vlanEnabled"))
    vlan_id = _as_vlan_id(vlan_value)
    if vlan_id is not None:
        return vlan_id
    if not vlan_enabled:
        return 1
    return None


def normalize_networks(networks: Iterable[object]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for network in _as_list(networks):
        if network is None:
            continue
        normalized.append(
            {
                "network_id": _first_attr(network, "_id", "id", "network_id", "networkId"),
                "name": _first_attr(network, "name", "network_name", "networkName"),
                "vlan_id": _network_vlan_id(network),
                "vlan_enabled": _as_bool(_first_attr(network, "vlan_enabled", "vlanEnabled")),
                "purpose": _first_attr(network, "purpose"),
            }
        )
    return normalized


def build_vlan_info(
    clients: Iterable[object], networks: Iterable[object]
) -> list[dict[str, object]]:
    vlan_counts = _client_vlan_counts(clients)
    vlan_entries = _network_vlan_entries(networks)
    for vlan_id, count in vlan_counts.items():
        entry = vlan_entries.setdefault(
            vlan_id,
            {"id": vlan_id, "name": None, "client_count": 0},
        )
        entry["client_count"] = count
    return [vlan_entries[key] for key in sorted(vlan_entries)]


def _client_vlan_counts(clients: Iterable[object]) -> dict[int, int]:
    vlan_counts: dict[int, int] = {}
    for client in _as_list(clients):
        vlan_id = _as_vlan_id(_first_attr(client, "vlan", "vlan_id", "vlanId", "vlanid"))
        if vlan_id is None:
            continue
        vlan_counts[vlan_id] = vlan_counts.get(vlan_id, 0) + 1
    return vlan_counts


def _network_vlan_entries(networks: Iterable[object]) -> dict[int, dict[str, object]]:
    vlan_entries: dict[int, dict[str, object]] = {}
    for network in normalize_networks(networks):
        vlan_id = network.get("vlan_id")
        if not isinstance(vlan_id, int):
            continue
        entry = vlan_entries.setdefault(
            vlan_id,
            {"id": vlan_id, "name": None, "client_count": 0},
        )
        name = network.get("name")
        if name and not entry["name"]:
            entry["name"] = name
    return vlan_entries
