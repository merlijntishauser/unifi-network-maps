"""Topology normalization and edge construction."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field

from .helpers import first_string_field, get_field, normalize_mac
from .labels import compose_port_label, order_edge_names
from .lldp import LLDPEntry, local_port_label
from .ports import extract_port_number

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Device:
    name: str
    model_name: str
    model: str
    mac: str
    ip: str
    type: str
    lldp_info: list[LLDPEntry]
    port_table: list[PortInfo] = field(default_factory=list)
    poe_ports: dict[int, bool] = field(default_factory=dict)
    uplink: UplinkInfo | None = None
    last_uplink: UplinkInfo | None = None
    version: str = ""


@dataclass(frozen=True)
class Edge:
    left: str
    right: str
    label: str | None = None
    poe: bool = False
    wireless: bool = False
    speed: int | None = None
    channel: int | None = None
    vlans: tuple[int, ...] = ()
    active_vlans: tuple[int, ...] = ()
    is_trunk: bool = False


type DeviceSource = object


@dataclass(frozen=True)
class UplinkInfo:
    mac: str | None
    name: str | None
    port: int | None


@dataclass(frozen=True)
class PortInfo:
    port_idx: int | None
    name: str | None
    ifname: str | None
    speed: int | None
    aggregation_group: str | None
    port_poe: bool
    poe_enable: bool
    poe_good: bool
    poe_power: float | None
    native_vlan: int | None = None
    tagged_vlans: tuple[int, ...] = ()
    wan_networkconf_id: str | None = None  # WAN assignment: "WAN", "WAN2", or network ID


@dataclass(frozen=True)
class WanInterface:
    """Information about a WAN interface on a gateway."""

    port_idx: int
    link_speed: int | None  # From API (Mbps)
    ip_address: str | None  # Public IP
    enabled: bool  # Port up/down
    label: str | None = None  # From CLI flag
    isp_speed: str | None = None  # From CLI flag


@dataclass(frozen=True)
class WanInfo:
    """WAN interface information for a gateway device."""

    wan1: WanInterface | None = None
    wan2: WanInterface | None = None


type PortMap = dict[tuple[str, str], str]
type PoeMap = dict[tuple[str, str], bool]
type SpeedMap = dict[tuple[str, str], int]
type ClientPortMap = dict[str, list[tuple[int, str]]]
type VlanMap = dict[tuple[str, str], tuple[int, ...]]


def _lldp_candidates(entry: LLDPEntry) -> list[str]:
    candidates: list[str] = []
    if entry.local_port_name:
        candidates.append(entry.local_port_name)
    if entry.port_id:
        candidates.append(entry.port_id)
    return candidates


def _match_port_by_name(candidates: list[str], port_table: list[PortInfo]) -> int | None:
    for candidate in candidates:
        normalized = candidate.strip().lower()
        for port in port_table:
            if port.ifname and port.ifname.strip().lower() == normalized:
                return port.port_idx
            if port.name and port.name.strip().lower() == normalized:
                return port.port_idx
    return None


def _match_port_by_number(candidates: list[str], port_table: list[PortInfo]) -> int | None:
    for candidate in candidates:
        number = extract_port_number(candidate)
        if number is None:
            continue
        for port in port_table:
            if port.port_idx == number:
                return port.port_idx
    return None


def _resolve_port_idx_from_lldp(lldp_entry: LLDPEntry, port_table: list[PortInfo]) -> int | None:
    if lldp_entry.local_port_idx is not None:
        return lldp_entry.local_port_idx
    candidates = _lldp_candidates(lldp_entry)
    matched = _match_port_by_name(candidates, port_table)
    if matched is not None:
        return matched
    return _match_port_by_number(candidates, port_table)


def classify_device_type(device: object) -> str:
    raw_type = get_field(device, "type")
    raw_name = get_field(device, "name")
    value = raw_type.strip().lower() if isinstance(raw_type, str) else ""
    if not value:
        name = raw_name.strip().lower() if isinstance(raw_name, str) else ""
        if "gateway" in name or name.startswith("gw"):
            return "gateway"
        if "switch" in name:
            return "switch"
        if "ap" in name:
            return "ap"
    if value in {"gateway", "ugw", "usg", "ux", "udm", "udr"}:
        return "gateway"
    if value in {"switch", "usw"}:
        return "switch"
    if value in {"uap", "ap"} or "ap" in value:
        return "ap"
    return "other"


# Client device category detection patterns
_CLIENT_NAME_PATTERNS: dict[str, tuple[str, ...]] = {
    "camera": ("camera", "cam", "doorbell", "uvc", "protect", "ring", "nest cam", "arlo"),
    "tv": ("tv", "television", "apple tv", "chromecast", "roku", "fire tv", "shield", "smart tv"),
    "phone": ("phone", "iphone", "android", "pixel", "galaxy", "mobile", "voip", "handset"),
    "printer": ("printer", "print", "laserjet", "inkjet", "epson", "canon", "brother", "hp "),
    "nas": ("nas", "synology", "qnap", "diskstation", "drobo", "freenas", "truenas"),
    "speaker": ("sonos", "homepod", "echo", "alexa", "google home", "speaker", "soundbar"),
    "game_console": ("playstation", "ps4", "ps5", "xbox", "nintendo", "switch", "steam deck"),
    "iot": ("sensor", "thermostat", "nest", "hue", "smart", "zigbee", "z-wave", "iot"),
}

# OUI/vendor patterns for manufacturer-based detection
_CLIENT_VENDOR_PATTERNS: dict[str, tuple[str, ...]] = {
    "camera": ("ubiquiti", "hikvision", "dahua", "axis", "ring", "arlo", "nest", "wyze"),
    "tv": ("samsung tv", "lg tv", "sony tv", "vizio", "tcl", "roku", "apple tv"),
    "phone": ("apple", "samsung mobile", "google pixel", "oneplus", "xiaomi"),
    "printer": ("hp inc", "canon", "epson", "brother", "lexmark", "xerox", "ricoh"),
    "nas": ("synology", "qnap", "western digital", "seagate", "netgear readynas"),
    "speaker": ("sonos", "bose", "harman", "bang & olufsen", "denon"),
    "game_console": ("sony interactive", "microsoft xbox", "nintendo"),
}

# UniFi product line mappings
_UNIFI_PRODUCT_CATEGORIES: dict[str, str] = {
    "protect": "camera",
    "talk": "phone",
    "access": "iot",
    "led": "iot",
    "connect": "iot",
}


def _classify_by_name(name: str) -> str | None:
    """Classify client by display name heuristics."""
    name_lower = name.lower()
    for category, patterns in _CLIENT_NAME_PATTERNS.items():
        for pattern in patterns:
            if pattern in name_lower:
                return category
    return None


def _classify_by_vendor(vendor: str) -> str | None:
    """Classify client by OUI/vendor name."""
    vendor_lower = vendor.lower()
    for category, patterns in _CLIENT_VENDOR_PATTERNS.items():
        for pattern in patterns:
            if pattern in vendor_lower:
                return category
    return None


def _classify_by_unifi_info(ucore: dict[str, object]) -> str | None:
    """Classify client by UniFi device info (product_line, model)."""
    product_line = ucore.get("product_line")
    if isinstance(product_line, str):
        line_lower = product_line.lower()
        for line_prefix, category in _UNIFI_PRODUCT_CATEGORIES.items():
            if line_lower.startswith(line_prefix):
                return category
    # Check model/shortname for specific device types
    for key in ("product_shortname", "computed_model", "product_model"):
        value = ucore.get(key)
        if isinstance(value, str):
            value_lower = value.lower()
            if any(cam in value_lower for cam in ("camera", "doorbell", "uvc", "g4", "g5")):
                return "camera"
            if "talk" in value_lower or "phone" in value_lower:
                return "phone"
    return None


def classify_client_type(client: object) -> str:
    """Classify a client into a device category.

    Detection priority:
    1. UniFi device info (product_line, model)
    2. Display name heuristics
    3. OUI/vendor patterns

    Returns one of: camera, tv, phone, printer, nas, speaker, game_console, iot, client
    """
    # Check UniFi device info first (most reliable)
    ucore = _client_ucore_info(client)
    if ucore:
        category = _classify_by_unifi_info(ucore)
        if category:
            return category

    # Check display name heuristics
    name = _client_display_name(client)
    if name:
        category = _classify_by_name(name)
        if category:
            return category

    # Check OUI/vendor
    vendor = _client_vendor(client)
    if vendor:
        category = _classify_by_vendor(vendor)
        if category:
            return category

    return "client"


def group_devices_by_type(devices: Iterable[Device]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {"gateway": [], "switch": [], "ap": [], "other": []}
    for device in devices:
        group = classify_device_type(device)
        groups[group].append(device.name)
    return groups


def _build_adjacency(edges: Iterable[Edge]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.left, set()).add(edge.right)
        adjacency.setdefault(edge.right, set()).add(edge.left)
    return adjacency


def _build_edge_map(edges: Iterable[Edge]) -> dict[frozenset[str], Edge]:
    return {frozenset({edge.left, edge.right}): edge for edge in edges}


def _tree_parents(adjacency: dict[str, set[str]], gateways: list[str]) -> dict[str, str]:
    visited: set[str] = set()
    parent: dict[str, str] = {}
    queue: deque[str] = deque()

    for gateway in gateways:
        if gateway in adjacency:
            visited.add(gateway)
            queue.append(gateway)

    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency.get(current, set())):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)
    return parent


def _tree_edges_from_parent(
    parent: dict[str, str], edge_map: dict[frozenset[str], Edge]
) -> list[Edge]:
    tree_edges: list[Edge] = []
    for child in sorted(parent):
        parent_name = parent[child]
        original = edge_map.get(frozenset({child, parent_name}))
        if original is None:
            tree_edges.append(Edge(left=parent_name, right=child))
        else:
            tree_edges.append(
                Edge(
                    left=parent_name,
                    right=child,
                    label=original.label,
                    poe=original.poe,
                    wireless=original.wireless,
                    speed=original.speed,
                    channel=original.channel,
                    vlans=original.vlans,
                    active_vlans=original.active_vlans,
                    is_trunk=original.is_trunk,
                )
            )
    return tree_edges


def build_tree_edges_by_topology(edges: Iterable[Edge], gateways: list[str]) -> list[Edge]:
    if not gateways:
        return []
    adjacency = _build_adjacency(edges)
    edge_map = _build_edge_map(edges)
    parent = _tree_parents(adjacency, gateways)
    return _tree_edges_from_parent(parent, edge_map)


def build_device_index(devices: Iterable[Device]) -> dict[str, str]:
    index: dict[str, str] = {}
    for device in devices:
        index[normalize_mac(device.mac)] = device.name
    return index


def _client_display_name(client: object) -> str | None:
    name = first_string_field(client, "name")
    if name:
        return name
    preferred = _client_ucore_display_name(client)
    if preferred:
        return preferred
    return first_string_field(client, "hostname", "mac")


def _client_uplink_mac(client: object) -> str | None:
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


def _client_uplink_port(client: object) -> int | None:
    for value in _client_port_values(client):
        parsed = _parse_port_value(value)
        if parsed is not None:
            return parsed
    return None


def _client_port_values(client: object) -> Iterable[object | None]:
    for key in ("uplink_remote_port", "sw_port", "ap_port", "port_idx"):
        yield get_field(client, key)
    for key in ("uplink", "last_uplink"):
        nested = get_field(client, key)
        if isinstance(nested, dict):
            for nested_key in ("uplink_remote_port", "port_idx"):
                yield nested.get(nested_key)


def _parse_port_value(value: object | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return extract_port_number(stripped)
    return None


def _client_is_wired(client: object) -> bool:
    return bool(get_field(client, "is_wired"))


def _client_unifi_flag(client: object) -> bool | None:
    for key in ("is_unifi", "is_unifi_device", "is_ubnt", "is_uap", "is_managed"):
        value = get_field(client, key)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
    return None


def _client_vendor(client: object) -> str | None:
    return first_string_field(
        client, "oui", "vendor", "vendor_name", "manufacturer", "manufacturer_name"
    )


def _client_ucore_info(client: object) -> dict[str, object] | None:
    info = get_field(client, "unifi_device_info_from_ucore")
    if isinstance(info, dict):
        return info
    return None


def _client_ucore_display_name(client: object) -> str | None:
    ucore = _client_ucore_info(client)
    if not ucore:
        return None
    return first_string_field(ucore, "name", "computed_model", "product_model", "product_shortname")


def _client_hostname_source(client: object) -> str | None:
    return first_string_field(client, "hostname_source")


def _client_is_unifi(client: object) -> bool:
    flag = _client_unifi_flag(client)
    if flag is not None:
        return flag
    ucore = _client_ucore_info(client)
    if ucore:
        managed = ucore.get("managed")
        if isinstance(managed, bool) and managed:
            return True
        if isinstance(ucore.get("product_line"), str) and ucore.get("product_line"):
            return True
        if isinstance(ucore.get("product_shortname"), str) and ucore.get("product_shortname"):
            return True
        for key in ("name", "computed_model", "product_model"):
            value = ucore.get(key)
            if isinstance(value, str) and value.strip():
                return True
    vendor = _client_vendor(client)
    if not vendor:
        return False
    normalized = vendor.lower()
    return "ubiquiti" in normalized or "unifi" in normalized


def _client_channel(client: object) -> int | None:
    for key in ("channel", "radio_channel", "wifi_channel"):
        value = get_field(client, key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _client_vlan(client: object) -> int | None:
    for key in ("vlan", "vlan_id", "vlanId", "vlanid"):
        value = get_field(client, key)
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)
    return None


def _client_matches_mode(client: object, mode: str) -> bool:
    wired = _client_is_wired(client)
    if mode == "all":
        return True
    if mode == "wireless":
        return not wired
    return wired


def _client_matches_filters(client: object, *, client_mode: str, only_unifi: bool) -> bool:
    if not _client_matches_mode(client, client_mode):
        return False
    if only_unifi and not _client_is_unifi(client):
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
    edges: list[Edge] = []
    seen: set[tuple[str, str]] = set()
    for client in clients:
        if not _client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
            continue
        name = _client_display_name(client)
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
        edges.append(
            Edge(
                left=device_name,
                right=name,
                label=label,
                wireless=is_wireless,
                channel=channel,
                vlans=vlans,
                active_vlans=vlans,  # Client's VLAN is always "active"
                is_trunk=False,
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
    node_types: dict[str, str] = {}
    for device in devices:
        node_types[device.name] = classify_device_type(device)
    if clients:
        for client in clients:
            if not _client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
                continue
            name = _client_display_name(client)
            if name:
                node_types[name] = classify_client_type(client)
    return node_types


def build_edges(
    devices: Iterable[Device],
    *,
    include_ports: bool = False,
    only_unifi: bool = True,
) -> list[Edge]:
    ordered_devices = sorted(devices, key=lambda item: (item.name.lower(), item.mac.lower()))
    index = build_device_index(ordered_devices)
    device_by_name = {device.name: device for device in ordered_devices}
    raw_links: list[tuple[str, str]] = []
    seen: set[frozenset[str]] = set()
    port_map: PortMap = {}
    poe_map: PoeMap = {}
    speed_map: SpeedMap = {}
    vlan_map: VlanMap = {}

    devices_with_lldp_edges = _collect_lldp_links(
        ordered_devices,
        index,
        port_map,
        poe_map,
        speed_map,
        vlan_map,
        raw_links,
        seen,
        only_unifi=only_unifi,
    )
    _collect_uplink_links(
        ordered_devices,
        devices_with_lldp_edges,
        index,
        device_by_name,
        port_map,
        raw_links,
        seen,
        include_ports=include_ports,
        only_unifi=only_unifi,
    )
    edges = _build_ordered_edges(
        raw_links,
        port_map,
        poe_map,
        speed_map,
        vlan_map,
        device_by_name,
        include_ports=include_ports,
    )

    poe_edges = sum(1 for edge in edges if edge.poe)
    logger.debug("Built %d unique edges (%d PoE)", len(edges), poe_edges)
    return edges


def build_port_map(devices: Iterable[Device], *, only_unifi: bool = True) -> PortMap:
    ordered_devices = sorted(devices, key=lambda item: (item.name.lower(), item.mac.lower()))
    index = build_device_index(ordered_devices)
    device_by_name = {device.name: device for device in ordered_devices}
    raw_links: list[tuple[str, str]] = []
    seen: set[frozenset[str]] = set()
    port_map: PortMap = {}
    poe_map: PoeMap = {}
    speed_map: SpeedMap = {}
    vlan_map: VlanMap = {}

    devices_with_lldp_edges = _collect_lldp_links(
        ordered_devices,
        index,
        port_map,
        poe_map,
        speed_map,
        vlan_map,
        raw_links,
        seen,
        only_unifi=only_unifi,
    )
    _collect_uplink_links(
        ordered_devices,
        devices_with_lldp_edges,
        index,
        device_by_name,
        port_map,
        raw_links,
        seen,
        include_ports=True,
        only_unifi=only_unifi,
    )
    return port_map


def build_client_port_map(
    devices: Iterable[Device],
    clients: Iterable[object],
    *,
    client_mode: str,
    only_unifi: bool = False,
) -> ClientPortMap:
    device_index = build_device_index(devices)
    port_map: ClientPortMap = {}
    for client in clients:
        if not _client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
            continue
        name = _client_display_name(client)
        uplink_mac = _client_uplink_mac(client)
        uplink_port = _client_uplink_port(client)
        if not name or not uplink_mac or uplink_port is None:
            continue
        device_name = device_index.get(normalize_mac(uplink_mac))
        if not device_name:
            continue
        port_map.setdefault(device_name, []).append((uplink_port, name))
    return port_map


def _port_speed_by_idx(port_table: list[PortInfo], port_idx: int) -> int | None:
    for port in port_table:
        if port.port_idx == port_idx:
            return port.speed
    return None


def _port_vlans_by_idx(port_table: list[PortInfo], port_idx: int) -> tuple[int, ...]:
    """Get all VLANs configured on a port (native + tagged)."""
    for port in port_table:
        if port.port_idx == port_idx:
            vlans: list[int] = []
            if port.native_vlan is not None:
                vlans.append(port.native_vlan)
            vlans.extend(port.tagged_vlans)
            return tuple(sorted(set(vlans)))
    return ()


def _populate_port_maps(
    device_name: str,
    peer_name: str,
    port_idx: int,
    poe_ports: dict[int, bool],
    port_table: list[PortInfo],
    poe_map: PoeMap,
    speed_map: SpeedMap,
    vlan_map: VlanMap,
) -> None:
    """Populate PoE, speed, and VLAN maps for an edge."""
    if port_idx in poe_ports:
        poe_map[(device_name, peer_name)] = poe_ports[port_idx]
    port_speed = _port_speed_by_idx(port_table, port_idx)
    if port_speed is not None:
        speed_map[(device_name, peer_name)] = port_speed
    port_vlans = _port_vlans_by_idx(port_table, port_idx)
    if port_vlans:
        vlan_map[(device_name, peer_name)] = port_vlans


def _collect_lldp_links(
    devices: list[Device],
    index: dict[str, str],
    port_map: PortMap,
    poe_map: PoeMap,
    speed_map: SpeedMap,
    vlan_map: VlanMap,
    raw_links: list[tuple[str, str]],
    seen: set[frozenset[str]],
    *,
    only_unifi: bool,
) -> set[str]:
    devices_with_lldp_edges: set[str] = set()
    for device in devices:
        poe_ports = device.poe_ports
        for lldp_entry in sorted(
            device.lldp_info,
            key=lambda item: (
                normalize_mac(item.chassis_id),
                str(item.port_id or ""),
                str(item.port_desc or ""),
            ),
        ):
            peer_mac = normalize_mac(lldp_entry.chassis_id)
            peer_name = index.get(peer_mac)
            if peer_name is None:
                if only_unifi:
                    continue
                peer_name = lldp_entry.chassis_id

            resolved_port_idx = _resolve_port_idx_from_lldp(lldp_entry, device.port_table)
            entry_for_label = (
                LLDPEntry(
                    chassis_id=lldp_entry.chassis_id,
                    port_id=lldp_entry.port_id,
                    port_desc=lldp_entry.port_desc,
                    local_port_name=lldp_entry.local_port_name,
                    local_port_idx=resolved_port_idx,
                )
                if resolved_port_idx is not None
                else lldp_entry
            )
            label = local_port_label(entry_for_label)
            if label:
                port_map[(device.name, peer_name)] = label
            if resolved_port_idx is not None:
                _populate_port_maps(
                    device.name,
                    peer_name,
                    resolved_port_idx,
                    poe_ports,
                    device.port_table,
                    poe_map,
                    speed_map,
                    vlan_map,
                )

            key = frozenset({device.name, peer_name})
            if key in seen:
                continue

            raw_links.append((device.name, peer_name))
            seen.add(key)
            devices_with_lldp_edges.add(device.name)
    return devices_with_lldp_edges


def _uplink_name(
    uplink: UplinkInfo | None,
    index: dict[str, str],
    *,
    only_unifi: bool,
) -> str | None:
    if not uplink:
        return None
    if uplink.mac:
        resolved = index.get(normalize_mac(uplink.mac))
        if resolved:
            return resolved
    if uplink.name:
        return uplink.name
    if not only_unifi and uplink.mac:
        return uplink.mac
    return None


def _maybe_add_uplink_link(
    device: Device,
    upstream_name: str,
    *,
    uplink: UplinkInfo | None,
    device_by_name: dict[str, Device],
    port_map: PortMap,
    raw_links: list[tuple[str, str]],
    seen: set[frozenset[str]],
    include_ports: bool,
) -> None:
    key = frozenset({device.name, upstream_name})
    if key in seen:
        return
    if uplink and uplink.port is not None:
        if include_ports:
            port_map[(upstream_name, device.name)] = f"Port {uplink.port}"
    raw_links.append((upstream_name, device.name))
    seen.add(key)


def _collect_uplink_links(
    devices: list[Device],
    devices_with_lldp_edges: set[str],
    index: dict[str, str],
    device_by_name: dict[str, Device],
    port_map: PortMap,
    raw_links: list[tuple[str, str]],
    seen: set[frozenset[str]],
    *,
    include_ports: bool,
    only_unifi: bool,
) -> None:
    for device in devices:
        if device.name in devices_with_lldp_edges:
            continue
        uplink = device.uplink or device.last_uplink
        upstream_name = _uplink_name(uplink, index, only_unifi=only_unifi)
        if not upstream_name:
            continue
        if only_unifi and upstream_name not in device_by_name:
            continue
        _maybe_add_uplink_link(
            device,
            upstream_name,
            uplink=uplink,
            device_by_name=device_by_name,
            port_map=port_map,
            raw_links=raw_links,
            seen=seen,
            include_ports=include_ports,
        )


def _build_ordered_edges(
    raw_links: list[tuple[str, str]],
    port_map: PortMap,
    poe_map: PoeMap,
    speed_map: SpeedMap,
    vlan_map: VlanMap,
    device_by_name: dict[str, Device],
    *,
    include_ports: bool,
) -> list[Edge]:
    type_rank = {"gateway": 0, "switch": 1, "ap": 2, "other": 3}

    def _rank_for_name(name: str) -> int:
        device = device_by_name.get(name)
        if not device:
            return 3
        return type_rank.get(classify_device_type(device), 3)

    edges: list[Edge] = []
    for source_name, target_name in raw_links:
        left_name = source_name
        right_name = target_name
        if include_ports:
            left_name, right_name = order_edge_names(
                left_name,
                right_name,
                port_map,
                _rank_for_name,
            )
        poe = poe_map.get((left_name, right_name), False) or poe_map.get(
            (right_name, left_name), False
        )
        speed = speed_map.get((left_name, right_name)) or speed_map.get((right_name, left_name))
        label = compose_port_label(left_name, right_name, port_map) if include_ports else None
        # Merge VLAN info from both directions: each side's port_table may
        # independently report the VLANs configured on this link.
        vlans_lr = vlan_map.get((left_name, right_name), ())
        vlans_rl = vlan_map.get((right_name, left_name), ())
        vlans = tuple(sorted(set(vlans_lr) | set(vlans_rl)))
        is_trunk = len(vlans) > 1
        edges.append(
            Edge(
                left=left_name,
                right=right_name,
                label=label,
                poe=poe,
                speed=speed,
                vlans=vlans,
                active_vlans=(),  # Will be populated later with client data
                is_trunk=is_trunk,
            )
        )
    return edges


def enrich_edges_with_active_vlans(
    edges: list[Edge],
    client_edges: list[Edge],
) -> list[Edge]:
    """Add active_vlans to edges based on client traffic."""
    # Build map of device -> set of active VLANs (from connected clients)
    device_active_vlans: dict[str, set[int]] = {}
    for client_edge in client_edges:
        device_name = client_edge.left  # Client edges have device on left
        for vlan in client_edge.active_vlans:
            device_active_vlans.setdefault(device_name, set()).add(vlan)

    # Enrich infrastructure edges with active VLANs
    enriched: list[Edge] = []
    for edge in edges:
        # Active VLANs are those configured on the link AND active on either endpoint
        left_active = device_active_vlans.get(edge.left, set())
        right_active = device_active_vlans.get(edge.right, set())
        combined_active = left_active | right_active
        active_vlans = tuple(sorted(set(edge.vlans) & combined_active))
        enriched.append(
            Edge(
                left=edge.left,
                right=edge.right,
                label=edge.label,
                poe=edge.poe,
                wireless=edge.wireless,
                speed=edge.speed,
                channel=edge.channel,
                vlans=edge.vlans,
                active_vlans=active_vlans,
                is_trunk=edge.is_trunk,
            )
        )
    return enriched


def collapse_client_edges(
    edges: list[Edge],
    node_types: dict[str, str],
) -> tuple[list[Edge], dict[str, int]]:
    """Collapse individual client edges into cluster nodes.

    Groups clients by their uplink device and replaces individual client edges
    with a single edge to a cluster node showing the client count.

    Args:
        edges: List of edges including client edges.
        node_types: Mutable dict mapping node names to types. Will be updated
            with new 'client_cluster' entries and individual clients removed.

    Returns:
        Tuple of (collapsed_edges, client_counts) where:
        - collapsed_edges: Edges with individual clients replaced by clusters
        - client_counts: Dict mapping device names to their client counts
    """
    client_counts: dict[str, int] = {}
    collapsed_edges: list[Edge] = []
    collapsed_clients: set[str] = set()

    for edge in edges:
        # Check if right side is a client (clients are always on right side of edge)
        if node_types.get(edge.right) == "client":
            client_counts[edge.left] = client_counts.get(edge.left, 0) + 1
            collapsed_clients.add(edge.right)
        else:
            collapsed_edges.append(edge)

    # Remove individual clients from node_types
    for client_name in collapsed_clients:
        node_types.pop(client_name, None)

    # Create cluster edges for devices with clients
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


@dataclass(frozen=True)
class TopologyResult:
    raw_edges: list[Edge]
    tree_edges: list[Edge]


def build_topology(
    devices: Iterable[Device],
    *,
    include_ports: bool,
    only_unifi: bool,
    gateways: list[str],
) -> TopologyResult:
    normalized_devices = list(devices)
    lldp_entries = sum(len(device.lldp_info) for device in normalized_devices)
    logger.debug(
        "Normalized %d devices (%d LLDP entries)",
        len(normalized_devices),
        lldp_entries,
    )
    raw_edges = build_edges(normalized_devices, include_ports=include_ports, only_unifi=only_unifi)
    tree_edges = build_tree_edges_by_topology(raw_edges, gateways)
    logger.debug(
        "Built %d hierarchy edges (gateways=%d)",
        len(tree_edges),
        len(gateways),
    )
    return TopologyResult(raw_edges=raw_edges, tree_edges=tree_edges)


def _normalize_wan_speed(speed: int | None) -> int | None:
    """Normalize WAN port speed to Mbps.

    Gateway devices report WAN port speeds in Gbps (e.g., 10 for 10G),
    while switches report in Mbps (e.g., 1000 for 1G). This function
    detects Gbps values and converts them to Mbps.

    Args:
        speed: Speed value from port table.

    Returns:
        Speed in Mbps, or None if not available.
    """
    if speed is None or speed == 0:
        return speed
    # Speeds 1-100 are likely in Gbps (1G to 100G), convert to Mbps
    # Speeds >= 100 are already in Mbps (100M+)
    if 1 <= speed <= 100:
        return speed * 1000
    return speed


def _find_wan_port_by_assignment(port_table: list[PortInfo], wan_id: str) -> PortInfo | None:
    """Find a WAN port by its wan_networkconf_id assignment.

    Args:
        port_table: List of port info from device.
        wan_id: WAN identifier to match (e.g., "WAN", "WAN2").

    Returns:
        PortInfo for the matching WAN port, or None if not found.
    """
    wan_id_lower = wan_id.lower()
    for port in port_table:
        if port.wan_networkconf_id:
            conf_id = port.wan_networkconf_id.lower()
            # Match exact WAN/WAN2 or network ID containing the WAN identifier
            if conf_id == wan_id_lower or wan_id_lower in conf_id:
                return port
    return None


def _find_wan_port_by_idx(port_table: list[PortInfo], port_idx: int) -> PortInfo | None:
    """Find a port by index (fallback for legacy detection)."""
    for port in port_table:
        if port.port_idx == port_idx:
            return port
    return None


def extract_wan_info(
    device: Device,
    *,
    wan1_label: str | None = None,
    wan1_isp_speed: str | None = None,
    wan2_label: str | None = None,
    wan2_isp_speed: str | None = None,
) -> WanInfo | None:
    """Extract WAN interface information from a gateway device.

    Detects WAN ports by their wan_networkconf_id assignment field. Falls back
    to legacy port number detection (port 1 for WAN1, port 9/2 for WAN2) if
    no WAN assignment is found.

    Args:
        device: The gateway device to extract WAN info from.
        wan1_label: Optional label for WAN1 (e.g., "KPN Fiber").
        wan1_isp_speed: Optional ISP speed for WAN1 (e.g., "1 Gbps ↓↑").
        wan2_label: Optional label for WAN2 (e.g., "Backup 4G").
        wan2_isp_speed: Optional ISP speed for WAN2.

    Returns:
        WanInfo with WAN interface details, or None if not a gateway.
    """
    device_type = classify_device_type(device)
    if device_type != "gateway":
        return None

    port_table = device.port_table
    if not port_table:
        return None

    # Find WAN1 port - first by assignment, then fallback to port 1
    wan1_port = _find_wan_port_by_assignment(port_table, "WAN")
    if not wan1_port:
        wan1_port = _find_wan_port_by_assignment(port_table, "WAN1")
    if not wan1_port:
        wan1_port = _find_wan_port_by_idx(port_table, 1)

    wan1 = None
    if wan1_port:
        wan1_speed = _normalize_wan_speed(wan1_port.speed)
        wan1 = WanInterface(
            port_idx=wan1_port.port_idx or 1,
            link_speed=wan1_speed,
            ip_address=device.ip if device.ip else None,
            enabled=wan1_speed is not None and wan1_speed > 0,
            label=wan1_label,
            isp_speed=wan1_isp_speed,
        )

    # Find WAN2 port - first by assignment, then fallback to port 9 or 2
    wan2_port = _find_wan_port_by_assignment(port_table, "WAN2")
    if not wan2_port:
        wan2_port = _find_wan_port_by_idx(port_table, 9)
    if not wan2_port:
        wan2_port = _find_wan_port_by_idx(port_table, 2)

    wan2 = None
    # Only include WAN2 if it has WAN assignment, or if label/speed specified, or active
    has_wan2_assignment = wan2_port and wan2_port.wan_networkconf_id
    has_wan2_cli_config = wan2_label or wan2_isp_speed
    wan2_speed = _normalize_wan_speed(wan2_port.speed) if wan2_port else None
    is_wan2_active = wan2_speed is not None and wan2_speed > 0
    if wan2_port and (has_wan2_assignment or has_wan2_cli_config or is_wan2_active):
        wan2 = WanInterface(
            port_idx=wan2_port.port_idx or 9,
            link_speed=wan2_speed,
            ip_address=None,  # WAN2 IP typically not in standard device data
            enabled=is_wan2_active,
            label=wan2_label,
            isp_speed=wan2_isp_speed,
        )

    if wan1 or wan2:
        return WanInfo(wan1=wan1, wan2=wan2)
    return None
