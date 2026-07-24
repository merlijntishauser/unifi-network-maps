"""Runtime data preparation for CLI rendering."""

from __future__ import annotations

import argparse
import logging

import yaml
from unifi_topology.adapters.config import Config
from unifi_topology.adapters.unifi import fetch_clients, fetch_devices, fetch_networks
from unifi_topology.model import build_node_names
from unifi_topology.model.clients import build_client_edges, build_client_port_map
from unifi_topology.model.edges import (
    build_topology,
    enrich_edges_with_active_vlans,
    group_devices_by_type,
)
from unifi_topology.model.topology import ClientPortMap, Device, TopologyResult, build_device_index
from unifi_topology.model.topology_coerce import normalize_devices
from unifi_topology.model.vlans import build_network_vlan_map
from unifi_topology.render.mermaid_theme import MermaidTheme

from ..io.debug import debug_dump_devices
from ..render.theme import resolve_themes

logger = logging.getLogger(__name__)


def load_devices_data(
    args: argparse.Namespace,
    config: Config | None,
    site: str,
    *,
    raw_devices_override: list[object] | None = None,
    raw_networks_override: list[object] | None = None,
) -> tuple[list[object], list[Device]]:
    if raw_devices_override is None:
        if config is None:
            raise ValueError("Config required to fetch devices")
        raw_devices = list(
            fetch_devices(config, site=site, detailed=True, use_cache=not args.no_cache)
        )
    else:
        raw_devices = raw_devices_override

    # Build network-to-VLAN mapping for resolving network IDs in port configs
    network_vlan_map: dict[str, int] | None = None
    if raw_networks_override is not None:
        network_vlan_map = build_network_vlan_map(raw_networks_override)
    elif config is not None:
        try:
            raw_networks = list(fetch_networks(config, site=site, use_cache=not args.no_cache))
            network_vlan_map = build_network_vlan_map(raw_networks)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Failed to fetch networks for VLAN resolution: %s", exc)

    devices = normalize_devices(raw_devices, network_vlan_map)
    if args.debug_dump:
        debug_dump_devices(raw_devices, devices, sample_count=max(0, args.debug_sample))
    return raw_devices, devices


def build_topology_data(
    args: argparse.Namespace,
    config: Config | None,
    site: str,
    *,
    include_ports: bool | None = None,
    raw_devices_override: list[object] | None = None,
    raw_networks_override: list[object] | None = None,
) -> tuple[list[Device], list[str], TopologyResult]:
    _raw_devices, devices = load_devices_data(
        args,
        config,
        site,
        raw_devices_override=raw_devices_override,
        raw_networks_override=raw_networks_override,
    )
    groups_for_rank = group_devices_by_type(devices)
    gateways = groups_for_rank.get("gateway", [])
    topology = build_topology(
        devices,
        include_ports=include_ports if include_ports is not None else args.include_ports,
        only_unifi=args.only_unifi,
        gateways=gateways,
    )
    return devices, gateways, topology


def build_edges_with_clients(
    args: argparse.Namespace,
    edges: list,
    devices: list[Device],
    config: Config | None,
    site: str,
    *,
    clients_override: list[object] | None = None,
    node_names: dict[str, str] | None = None,
) -> tuple[list, list | None]:
    clients = None
    client_edges: list = []
    if args.include_clients:
        if clients_override is None:
            if config is None:
                raise ValueError("Config required to fetch clients")
            try:
                clients = list(fetch_clients(config, site=site, use_cache=not args.no_cache))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to fetch clients; skipping client edges: %s", exc)
                return edges, None
        else:
            clients = clients_override
        device_index = build_device_index(devices)
        client_edges = build_client_edges(
            clients,
            device_index,
            include_ports=args.include_ports,
            client_mode=args.client_scope,
            only_unifi=args.only_unifi,
            node_names=node_names,
        )
    # Enrich infrastructure edges with active VLANs from client traffic
    enriched_edges = enrich_edges_with_active_vlans(edges, client_edges)
    return enriched_edges + client_edges, clients


def select_edges(topology: TopologyResult) -> tuple[list, bool]:
    if topology.tree_edges:
        return topology.tree_edges, True
    logging.warning("No gateway found for hierarchy; rendering raw edges.")
    return topology.raw_edges, False


def load_topology_for_render(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_networks: list[object] | None = None,
) -> tuple[list[Device], TopologyResult] | None:
    try:
        include_ports = True if args.format == "mkdocs" else None
        devices, _gateways, topology = build_topology_data(
            args,
            config,
            site,
            include_ports=include_ports,
            raw_devices_override=mock_devices,
            raw_networks_override=mock_networks,
        )
    except Exception as exc:
        logging.error("Failed to build topology: %s", exc)
        return None
    return devices, topology


def load_dark_mermaid_theme() -> MermaidTheme | None:
    try:
        dark_theme, _ = resolve_themes(theme_name="classic-dark")
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        logger.warning("Failed to load dark theme: %s", exc)
        return None
    return dark_theme


def resolve_mkdocs_client_ports(
    args: argparse.Namespace,
    devices: list[Device],
    config: Config | None,
    site: str,
    mock_clients: list[object] | None,
) -> tuple[ClientPortMap | None, dict[str, str] | None, int | None]:
    if not args.include_clients:
        return None, None, None
    if mock_clients is None:
        if config is None:
            return None, None, 2
        try:
            clients = list(fetch_clients(config, site=site))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch clients for MkDocs: %s", exc)
            return None, None, None
    else:
        clients = mock_clients
    client_ports = build_client_port_map(
        devices,
        clients,
        client_mode=args.client_scope,
        only_unifi=args.only_unifi,
    )
    client_node_names = build_node_names(
        devices,
        clients,
        client_mode=args.client_scope,
        only_unifi=args.only_unifi,
    )
    return client_ports, client_node_names, None
