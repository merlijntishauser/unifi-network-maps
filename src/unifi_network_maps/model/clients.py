"""Client handling and edge building."""

from __future__ import annotations

from collections.abc import Iterable

from .classify import (
    classify_client_type,
    classify_device_type,
    client_display_name,
    client_is_unifi,
)
from .connection import ConnectionInfo, classify_signal_quality
from .helpers import first_string_field, get_field, normalize_mac
from .ports import extract_port_number
from .topology import ClientPortMap, Device, Edge


def _client_uplink_mac(client: object) -> str | None:
    """Get the MAC address of the device this client is connected to."""
    mac = first_string_field(
        client, "ap_mac", "sw_mac", "uplink_mac", "uplink_device_mac", "last_uplink_mac"
    )
    if mac:
        return mac
    for key in ("uplink", "last_uplink"):
        nested = get_field(client, key)
        if isinstance(nested, dict):
            mac = first_string_field(nested, "uplink_mac", "uplink_device_mac")
            if mac:
                return mac
    return None


def _client_port_values(client: object) -> Iterable[object | None]:
    """Yield all possible port values from client data."""
    for key in ("uplink_remote_port", "sw_port", "ap_port", "port_idx"):
        yield get_field(client, key)
    for key in ("uplink", "last_uplink"):
        nested = get_field(client, key)
        if isinstance(nested, dict):
            for nested_key in ("uplink_remote_port", "port_idx"):
                yield nested.get(nested_key)


def _parse_port_value(value: object | None) -> int | None:
    """Parse a port value to int."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return extract_port_number(stripped)
    return None


def _client_uplink_port(client: object) -> int | None:
    """Get the port number this client is connected to."""
    for value in _client_port_values(client):
        parsed = _parse_port_value(value)
        if parsed is not None:
            return parsed
    return None


def _client_is_wired(client: object) -> bool:
    """Check if client is wired."""
    return bool(get_field(client, "is_wired"))


def _client_channel(client: object) -> int | None:
    """Get wireless channel for client."""
    for key in ("channel", "radio_channel", "wifi_channel"):
        value = get_field(client, key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _client_vlan(client: object) -> int | None:
    """Get VLAN ID for client."""
    for key in ("vlan", "vlan_id", "vlanId", "vlanid"):
        value = get_field(client, key)
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)
    return None


def _extract_connection_info(client: object) -> ConnectionInfo | None:
    """Extract connection quality metrics for wireless clients."""
    if _client_is_wired(client):
        return None

    signal = get_field(client, "signal")
    noise = get_field(client, "noise")
    tx_rate = get_field(client, "tx_rate")
    rx_rate = get_field(client, "rx_rate")
    satisfaction = get_field(client, "satisfaction")

    signal_dbm = int(signal) if isinstance(signal, int | float) else None
    noise_dbm = int(noise) if isinstance(noise, int | float) else None
    tx_rate_mbps = int(tx_rate) if isinstance(tx_rate, int | float) else None
    rx_rate_mbps = int(rx_rate) if isinstance(rx_rate, int | float) else None
    satisfaction_val = int(satisfaction) if isinstance(satisfaction, int | float) else None

    return ConnectionInfo(
        signal_dbm=signal_dbm,
        noise_dbm=noise_dbm,
        tx_rate_mbps=tx_rate_mbps,
        rx_rate_mbps=rx_rate_mbps,
        satisfaction=satisfaction_val,
        quality=classify_signal_quality(signal_dbm),
    )


def _client_matches_mode(client: object, mode: str) -> bool:
    """Check if client matches wired/wireless mode filter."""
    wired = _client_is_wired(client)
    if mode == "all":
        return True
    if mode == "wireless":
        return not wired
    return wired


def client_matches_filters(client: object, *, client_mode: str, only_unifi: bool) -> bool:
    """Check if client matches all filters."""
    if not _client_matches_mode(client, client_mode):
        return False
    if only_unifi and not client_is_unifi(client):
        return False
    return True


def build_client_edges(
    clients: Iterable[object],
    device_index: dict[str, str],
    *,
    include_ports: bool = False,
    client_mode: str = "wired",
    only_unifi: bool = False,
) -> list[Edge]:
    """Build edges from devices to their connected clients."""
    edges: list[Edge] = []
    seen: set[tuple[str, str]] = set()
    for client in clients:
        if not client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
            continue
        name = client_display_name(client)
        uplink_mac = _client_uplink_mac(client)
        if not name or not uplink_mac:
            continue
        device_name = device_index.get(normalize_mac(uplink_mac))
        if not device_name:
            continue
        label = None
        if include_ports:
            uplink_port = _client_uplink_port(client)
            if uplink_port is not None:
                label = f"{device_name}: Port {uplink_port} <-> {name}"
        key = (device_name, name)
        if key in seen:
            continue
        is_wireless = not _client_is_wired(client)
        channel = _client_channel(client) if is_wireless else None
        client_vlan = _client_vlan(client)
        vlans = (client_vlan,) if client_vlan else ()
        connection = _extract_connection_info(client)
        edges.append(
            Edge(
                left=device_name,
                right=name,
                label=label,
                wireless=is_wireless,
                channel=channel,
                vlans=vlans,
                active_vlans=vlans,
                is_trunk=False,
                connection=connection,
            )
        )
        seen.add(key)
    return edges


def build_node_type_map(
    devices: Iterable[Device],
    clients: Iterable[object] | None = None,
    *,
    client_mode: str = "wired",
    only_unifi: bool = False,
) -> dict[str, str]:
    """Build a map of node names to their types."""
    node_types: dict[str, str] = {}
    for device in devices:
        node_types[device.name] = classify_device_type(device)
    if clients:
        for client in clients:
            if not client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
                continue
            name = client_display_name(client)
            if name:
                node_types[name] = classify_client_type(client)
    return node_types


def build_client_port_map(
    devices: Iterable[Device],
    clients: Iterable[object],
    *,
    client_mode: str,
    only_unifi: bool = False,
) -> ClientPortMap:
    """Build a map of device names to their connected client ports."""
    from .topology import build_device_index

    device_index = build_device_index(devices)
    port_map: ClientPortMap = {}
    for client in clients:
        if not client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
            continue
        name = client_display_name(client)
        uplink_mac = _client_uplink_mac(client)
        uplink_port = _client_uplink_port(client)
        if not name or not uplink_mac or uplink_port is None:
            continue
        device_name = device_index.get(normalize_mac(uplink_mac))
        if not device_name:
            continue
        port_map.setdefault(device_name, []).append((uplink_port, name))
    return port_map


def collapse_client_edges(
    edges: list[Edge],
    node_types: dict[str, str],
) -> tuple[list[Edge], dict[str, int]]:
    """Collapse individual client edges into cluster nodes."""
    client_counts: dict[str, int] = {}
    collapsed_edges: list[Edge] = []
    collapsed_clients: set[str] = set()

    for edge in edges:
        if node_types.get(edge.right) == "client":
            client_counts[edge.left] = client_counts.get(edge.left, 0) + 1
            collapsed_clients.add(edge.right)
        else:
            collapsed_edges.append(edge)

    for client_name in collapsed_clients:
        node_types.pop(client_name, None)

    for device_name, count in sorted(client_counts.items()):
        cluster_name = f"{device_name} ({count} clients)"
        collapsed_edges.append(
            Edge(
                left=device_name,
                right=cluster_name,
                label=None,
                poe=False,
                wireless=False,
            )
        )
        node_types[cluster_name] = "client_cluster"

    return collapsed_edges, client_counts
