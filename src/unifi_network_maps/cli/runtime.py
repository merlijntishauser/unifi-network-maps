"""Runtime data preparation for CLI rendering."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..adapters.config import Config
from ..adapters.unifi import fetch_clients, fetch_devices
from ..io.debug import debug_dump_devices
from ..model.topology import (
    ClientPortMap,
    Device,
    TopologyResult,
    build_client_edges,
    build_client_port_map,
    build_device_index,
    build_topology,
    group_devices_by_type,
    normalize_devices,
)
from ..render.mermaid_theme import MermaidTheme
from ..render.theme import load_theme

logger = logging.getLogger(__name__)


def load_devices_data(
    args: argparse.Namespace,
    config: Config | None,
    site: str,
    *,
    raw_devices_override: list[object] | None = None,
) -> tuple[list[object], list[Device]]:
    if raw_devices_override is None:
        if config is None:
            raise ValueError("Config required to fetch devices")
        raw_devices = list(
            fetch_devices(config, site=site, detailed=True, use_cache=not args.no_cache)
        )
    else:
        raw_devices = raw_devices_override
    devices = normalize_devices(raw_devices)
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
) -> tuple[list[Device], list[str], TopologyResult]:
    _raw_devices, devices = load_devices_data(
        args,
        config,
        site,
        raw_devices_override=raw_devices_override,
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
) -> tuple[list, list | None]:
    clients = None
    if args.include_clients:
        if clients_override is None:
            if config is None:
                raise ValueError("Config required to fetch clients")
            clients = list(fetch_clients(config, site=site, use_cache=not args.no_cache))
        else:
            clients = clients_override
        device_index = build_device_index(devices)
        edges = edges + build_client_edges(
            clients,
            device_index,
            include_ports=args.include_ports,
            client_mode=args.client_scope,
            only_unifi=args.only_unifi,
        )
    return edges, clients


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
) -> tuple[list[Device], TopologyResult] | None:
    try:
        include_ports = True if args.format == "mkdocs" else None
        devices, _gateways, topology = build_topology_data(
            args,
            config,
            site,
            include_ports=include_ports,
            raw_devices_override=mock_devices,
        )
    except Exception as exc:
        logging.error("Failed to build topology: %s", exc)
        return None
    return devices, topology


def load_dark_mermaid_theme() -> MermaidTheme | None:
    dark_theme_path = Path(__file__).resolve().parents[1] / "assets" / "themes" / "dark.yaml"
    try:
        dark_theme, _ = load_theme(dark_theme_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load dark theme: %s", exc)
        return None
    return dark_theme


def resolve_mkdocs_client_ports(
    args: argparse.Namespace,
    devices: list[Device],
    config: Config | None,
    site: str,
    mock_clients: list[object] | None,
) -> tuple[ClientPortMap | None, int | None]:
    if not args.include_clients:
        return None, None
    if mock_clients is None:
        if config is None:
            return None, 2
        clients = list(fetch_clients(config, site=site))
    else:
        clients = mock_clients
    client_ports = build_client_port_map(
        devices,
        clients,
        client_mode=args.client_scope,
        only_unifi=args.only_unifi,
    )
    return client_ports, None
