"""Edge building and topology construction."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Iterable

from .classify import classify_device_type
from .helpers import normalize_mac
from .labels import compose_port_label, order_edge_names
from .lldp import LLDPEntry, local_port_label
from .ports import extract_port_number
from .topology import (
    Device,
    Edge,
    PoeMap,
    PortInfo,
    PortMap,
    SpeedMap,
    TopologyResult,
    UplinkInfo,
    VlanMap,
)

logger = logging.getLogger(__name__)


def build_device_index(devices: Iterable[Device]) -> dict[str, str]:
    """Build MAC to name index for devices."""
    index: dict[str, str] = {}
    for device in devices:
        index[normalize_mac(device.mac)] = device.name
    return index


def _lldp_candidates(entry: LLDPEntry) -> list[str]:
    """Get candidate port identifiers from LLDP entry."""
    candidates: list[str] = []
    if entry.local_port_name:
        candidates.append(entry.local_port_name)
    if entry.port_id:
        candidates.append(entry.port_id)
    return candidates


def _match_port_by_name(candidates: list[str], port_table: list[PortInfo]) -> int | None:
    """Match port by name/ifname."""
    for candidate in candidates:
        normalized = candidate.strip().lower()
        for port in port_table:
            if port.ifname and port.ifname.strip().lower() == normalized:
                return port.port_idx
            if port.name and port.name.strip().lower() == normalized:
                return port.port_idx
    return None


def _match_port_by_number(candidates: list[str], port_table: list[PortInfo]) -> int | None:
    """Match port by extracted number."""
    for candidate in candidates:
        number = extract_port_number(candidate)
        if number is None:
            continue
        for port in port_table:
            if port.port_idx == number:
                return port.port_idx
    return None


def _resolve_port_idx_from_lldp(lldp_entry: LLDPEntry, port_table: list[PortInfo]) -> int | None:
    """Resolve port index from LLDP entry."""
    if lldp_entry.local_port_idx is not None:
        return lldp_entry.local_port_idx
    candidates = _lldp_candidates(lldp_entry)
    matched = _match_port_by_name(candidates, port_table)
    if matched is not None:
        return matched
    return _match_port_by_number(candidates, port_table)


def _find_port_by_idx(port_table: list[PortInfo], port_idx: int) -> PortInfo | None:
    """Find port entry by index."""
    for port in port_table:
        if port.port_idx == port_idx:
            return port
    return None


def _port_speed_by_idx(port_table: list[PortInfo], port_idx: int) -> int | None:
    """Get port speed by index."""
    port = _find_port_by_idx(port_table, port_idx)
    return port.speed if port else None


def _port_vlans_by_idx(port_table: list[PortInfo], port_idx: int) -> tuple[int, ...]:
    """Get all VLANs configured on a port (native + tagged)."""
    port = _find_port_by_idx(port_table, port_idx)
    if not port:
        return ()
    vlans: list[int] = []
    if port.native_vlan is not None:
        vlans.append(port.native_vlan)
    vlans.extend(port.tagged_vlans)
    return tuple(sorted(set(vlans)))


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
    """Collect edges from LLDP data."""
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
    """Get upstream device name from uplink info."""
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
    port_map: PortMap,
    raw_links: list[tuple[str, str]],
    seen: set[frozenset[str]],
    include_ports: bool,
) -> None:
    """Add uplink-based edge if not already seen."""
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
    """Collect edges from uplink data (fallback for devices without LLDP)."""
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
    """Build ordered Edge objects from raw links."""
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
        # Use None-aware lookup to handle speed=0 correctly
        speed = speed_map.get((left_name, right_name))
        if speed is None:
            speed = speed_map.get((right_name, left_name))
        label = compose_port_label(left_name, right_name, port_map) if include_ports else None
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
                active_vlans=(),
                is_trunk=is_trunk,
            )
        )
    return edges


def build_edges(
    devices: Iterable[Device],
    *,
    include_ports: bool = False,
    only_unifi: bool = True,
) -> list[Edge]:
    """Build edges between devices from LLDP and uplink data."""
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
    """Build port label map from device data."""
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


def _build_adjacency(edges: Iterable[Edge]) -> dict[str, set[str]]:
    """Build adjacency list from edges."""
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.left, set()).add(edge.right)
        adjacency.setdefault(edge.right, set()).add(edge.left)
    return adjacency


def _build_edge_map(edges: Iterable[Edge]) -> dict[frozenset[str], Edge]:
    """Build edge lookup map."""
    return {frozenset({edge.left, edge.right}): edge for edge in edges}


def _tree_parents(adjacency: dict[str, set[str]], gateways: list[str]) -> dict[str, str]:
    """BFS to find parent for each node in tree."""
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
    """Build tree edges from parent map."""
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
    """Build tree edges rooted at gateways using BFS."""
    if not gateways:
        return []
    adjacency = _build_adjacency(edges)
    edge_map = _build_edge_map(edges)
    parent = _tree_parents(adjacency, gateways)
    return _tree_edges_from_parent(parent, edge_map)


def enrich_edges_with_active_vlans(
    edges: list[Edge],
    client_edges: list[Edge],
) -> list[Edge]:
    """Add active_vlans to edges based on client traffic."""
    device_active_vlans: dict[str, set[int]] = {}
    for client_edge in client_edges:
        device_name = client_edge.left
        for vlan in client_edge.active_vlans:
            device_active_vlans.setdefault(device_name, set()).add(vlan)

    enriched: list[Edge] = []
    for edge in edges:
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


def build_topology(
    devices: Iterable[Device],
    *,
    include_ports: bool,
    only_unifi: bool,
    gateways: list[str],
) -> TopologyResult:
    """Build complete topology from devices."""
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


def group_devices_by_type(devices: Iterable[Device]) -> dict[str, list[str]]:
    """Group devices by their type."""
    groups: dict[str, list[str]] = {"gateway": [], "switch": [], "ap": [], "other": []}
    for device in devices:
        group = classify_device_type(device)
        groups[group].append(device.name)
    return groups


def _primary_vlan_for_node(
    node: str,
    edges: list[Edge],
) -> int | None:
    """Find the primary VLAN for a node from its edges.

    Uses active_vlans first, falls back to vlans, picks lowest VLAN ID.
    """
    vlans: set[int] = set()
    for edge in edges:
        if edge.left != node and edge.right != node:
            continue
        if edge.active_vlans:
            vlans.update(edge.active_vlans)
        elif edge.vlans:
            vlans.update(edge.vlans)
    return min(vlans) if vlans else None


def group_nodes_by_vlan(
    edges: list[Edge],
    vlan_names: dict[int, str] | None = None,
) -> tuple[dict[str, list[str]], list[str], dict[str, int]]:
    """Group nodes by their primary VLAN membership.

    Returns (groups, group_order, group_vlan_ids) where groups maps VLAN name
    to node list, group_order sorts by VLAN ID ascending with "Unassigned" last,
    and group_vlan_ids maps group name to its VLAN ID.
    """
    vlan_names = vlan_names or {}
    nodes: set[str] = set()
    for edge in edges:
        nodes.add(edge.left)
        nodes.add(edge.right)

    vlan_groups: dict[int, list[str]] = {}
    unassigned: list[str] = []

    for node in sorted(nodes):
        vlan_id = _primary_vlan_for_node(node, edges)
        if vlan_id is None:
            unassigned.append(node)
        else:
            vlan_groups.setdefault(vlan_id, []).append(node)

    groups: dict[str, list[str]] = {}
    group_vlan_ids: dict[str, int] = {}
    group_order: list[str] = []

    for vlan_id in sorted(vlan_groups):
        name = vlan_names.get(vlan_id, f"VLAN {vlan_id}")
        groups[name] = vlan_groups[vlan_id]
        group_vlan_ids[name] = vlan_id
        group_order.append(name)

    if unassigned:
        groups["Unassigned"] = unassigned
        group_order.append("Unassigned")

    return groups, group_order, group_vlan_ids
