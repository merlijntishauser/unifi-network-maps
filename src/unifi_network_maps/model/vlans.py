"""VLAN inventory helpers."""

from __future__ import annotations

from collections.abc import Iterable

from .helpers import as_bool, as_list, first_attr


def _as_vlan_id(value: object | None) -> int | None:
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        return int(value) if value.isdigit() and int(value) > 0 else None
    return None


def _network_vlan_id(network: object) -> int | None:
    vlan_value = first_attr(network, "vlan", "vlan_id", "vlanId", "vlanid")
    vlan_enabled = as_bool(first_attr(network, "vlan_enabled", "vlanEnabled"))
    vlan_id = _as_vlan_id(vlan_value)
    if vlan_id is not None:
        return vlan_id
    if not vlan_enabled:
        return 1
    return None


def normalize_networks(networks: Iterable[object]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for network in as_list(networks):
        if network is None:
            continue
        raw_enabled = first_attr(network, "enabled", "wan_enabled")
        normalized.append(
            {
                "network_id": first_attr(network, "_id", "id", "network_id", "networkId"),
                "name": first_attr(network, "name", "network_name", "networkName"),
                "vlan_id": _network_vlan_id(network),
                "vlan_enabled": as_bool(first_attr(network, "vlan_enabled", "vlanEnabled")),
                "purpose": first_attr(network, "purpose"),
                "enabled": as_bool(raw_enabled) if raw_enabled is not None else None,
            }
        )
    return normalized


def build_wan_enabled_map(networks: Iterable[object]) -> dict[str, bool]:
    """Build a mapping from WAN purpose to enabled state.

    Returns e.g. ``{"wan": True, "wan2": False}``.  Only includes entries
    where the ``enabled`` field is explicitly set in the network config.
    """
    result: dict[str, bool] = {}
    for network in normalize_networks(networks):
        purpose = network.get("purpose")
        enabled = network.get("enabled")
        if isinstance(purpose, str) and purpose.startswith("wan") and enabled is not None:
            result[purpose] = bool(enabled)
    return result


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
    for client in as_list(clients):
        vlan_id = _as_vlan_id(first_attr(client, "vlan", "vlan_id", "vlanId", "vlanid"))
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


def build_network_vlan_map(networks: Iterable[object]) -> dict[str, int]:
    """Build a mapping from network ID to VLAN ID for WLAN resolution."""
    result: dict[str, int] = {}
    for network in normalize_networks(networks):
        network_id = network.get("network_id")
        vlan_id = network.get("vlan_id")
        if isinstance(network_id, str) and isinstance(vlan_id, int):
            result[network_id] = vlan_id
    return result


def build_vlan_names(networks: Iterable[object]) -> dict[int, str]:
    """Build a mapping from VLAN ID to network name."""
    result: dict[int, str] = {}
    for network in normalize_networks(networks):
        vlan_id = network.get("vlan_id")
        name = network.get("name")
        if isinstance(vlan_id, int) and isinstance(name, str) and vlan_id not in result:
            result[vlan_id] = name
    return result
