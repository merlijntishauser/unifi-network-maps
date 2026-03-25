"""CLI rendering orchestration."""

from __future__ import annotations

import argparse
import logging

from unifi_topology.adapters.config import Config
from unifi_topology.adapters.dns import resolve_hostnames
from unifi_topology.adapters.unifi import fetch_clients, fetch_networks
from unifi_topology.model import build_node_names
from unifi_topology.model.classify import classify_device_type
from unifi_topology.model.clients import build_node_type_map, collapse_client_edges
from unifi_topology.model.edges import build_port_map, group_devices_by_type, group_nodes_by_vlan
from unifi_topology.model.inventory import build_client_inventory, build_device_inventory
from unifi_topology.model.topology import Device, Edge, TopologyResult, WanInfo
from unifi_topology.model.vlans import build_vlan_names, build_wan_enabled_map
from unifi_topology.model.wan import extract_wan_info
from unifi_topology.render.inventory import render_device_inventory_table
from unifi_topology.render.lldp import render_lldp_md
from unifi_topology.render.mermaid import render_mermaid
from unifi_topology.render.mermaid_theme import MermaidTheme
from unifi_topology.render.svg import render_svg
from unifi_topology.render.svg_theme import SvgOptions, SvgTheme

from ..io.export import write_output
from ..io.mkdocs_assets import write_mkdocs_sidebar_assets
from ..render.legend import resolve_legend_style
from ..render.mkdocs import MkdocsRenderOptions, render_mkdocs
from .runtime import (
    build_edges_with_clients,
    load_dark_mermaid_theme,
    load_devices_data,
    load_topology_for_render,
    resolve_mkdocs_client_ports,
    select_edges,
)


def render_mermaid_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: TopologyResult,
    config: Config | None,
    site: str,
    mermaid_theme: MermaidTheme,
    *,
    clients_override: list[object] | None = None,
    networks_override: list[object] | None = None,
) -> str:
    edges, _has_tree = select_edges(topology)
    edges, clients = build_edges_with_clients(
        args,
        edges,
        devices,
        config,
        site,
        clients_override=clients_override,
        node_names=topology.node_names,
    )
    node_names = build_node_names(
        devices, clients, client_mode=args.client_scope, only_unifi=args.only_unifi
    )
    groups = None
    group_order = None
    if args.group_by_type:
        groups = group_devices_by_type(devices)
        group_order = ["gateway", "switch", "ap", "other"]
    networks = _fetch_networks_for_wan(config, site, networks_override=networks_override)
    wan_info = _extract_gateway_wan_info(devices, args, networks=networks)
    content = render_mermaid(
        edges,
        direction=args.direction,
        groups=groups,
        group_order=group_order,
        node_types=build_node_type_map(
            devices,
            clients,
            client_mode=args.client_scope,
            only_unifi=args.only_unifi,
        ),
        node_names=node_names,
        theme=mermaid_theme,
        wan_info=wan_info,
    )
    if args.markdown:
        content = f"""```mermaid
{content}```
"""
    return content


def _extract_gateway_wan_info(
    devices: list[Device],
    args: argparse.Namespace,
    *,
    networks: list[object] | None = None,
) -> WanInfo | None:
    """Extract WAN info from the first gateway device."""
    wan_enabled_map = build_wan_enabled_map(networks) if networks else None
    wan2_disabled = getattr(args, "wan2_disabled", "auto")
    for device in devices:
        if classify_device_type(device) == "gateway":
            return extract_wan_info(
                device,
                wan1_label=getattr(args, "wan_label", None),
                wan1_isp_speed=getattr(args, "wan_speed", None),
                wan2_label=getattr(args, "wan2_label", None),
                wan2_isp_speed=getattr(args, "wan2_speed", None),
                wan_enabled_map=wan_enabled_map,
                wan2_disabled=wan2_disabled,
            )
    return None


def _apply_client_clustering(
    edges: list[Edge],
    node_types: dict[str, str],
    layout_mode: str,
    groups: dict[str, list[str]] | None,
    group_order: list[str] | None,
    *,
    node_names: dict[str, str] | None = None,
) -> tuple[list[Edge], dict[str, list[str]] | None, list[str] | None]:
    """Apply client clustering and update groups if needed."""
    edges, _counts = collapse_client_edges(edges, node_types, node_names=node_names)
    if layout_mode in ("grouped", "vlan") and group_order and "client_cluster" not in group_order:
        group_order = [*group_order, "client_cluster"]
        if groups is not None:
            groups = {
                **groups,
                "client_cluster": [n for n, t in node_types.items() if t == "client_cluster"],
            }
    return edges, groups, group_order


def _fetch_networks_for_wan(
    config: Config | None,
    site: str,
    *,
    networks_override: list[object] | None = None,
) -> list[object] | None:
    """Fetch networks for WAN status detection, with cache fallback."""
    if networks_override is not None:
        return networks_override
    if config is None:
        return None
    try:
        return list(fetch_networks(config, site=site, use_cache=True))
    except Exception:  # noqa: BLE001
        return None


def _extract_dns_server(config: Config | None) -> str | None:
    """Extract the DNS server host from the controller URL."""
    if config is None:
        return None
    from urllib.parse import urlparse

    parsed = urlparse(config.url)
    return parsed.hostname


def _should_resolve_hostnames(args: argparse.Namespace) -> bool:
    """Determine whether to resolve hostnames based on args and format."""
    flag = getattr(args, "resolve_hostnames", None)
    if flag is not None:
        return flag
    return getattr(args, "format", "") == "mkdocs"


def _build_infrastructure_table(
    args: argparse.Namespace,
    devices: list[Device],
    config: Config | None,
    *,
    clients: list[object] | None = None,
) -> str:
    """Build the infrastructure inventory table, optionally with clients."""
    do_resolve = _should_resolve_hostnames(args)
    hostnames: dict[str, str] | None = None
    if do_resolve:
        dns_server = _extract_dns_server(config)
        if dns_server:
            all_ips = [d.ip for d in devices if d.ip]
            if clients:
                from unifi_topology.model.helpers import get_field

                for c in clients:
                    ip = get_field(c, "ip")
                    if isinstance(ip, str) and ip:
                        all_ips.append(ip)
            hostnames = resolve_hostnames(all_ips, dns_server)
    inventory = build_device_inventory(devices, hostnames)
    if clients:
        client_inventory = build_client_inventory(
            clients,
            hostnames,
            client_mode=getattr(args, "client_scope", "all"),
            only_unifi=getattr(args, "only_unifi", False),
        )
        inventory.extend(client_inventory)
    if not inventory:
        return ""
    return render_device_inventory_table(inventory, include_hostname=do_resolve)


def render_svg_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: TopologyResult,
    config: Config | None,
    site: str,
    svg_theme: SvgTheme,
    *,
    clients_override: list[object] | None = None,
    networks_override: list[object] | None = None,
) -> str:
    edges, _has_tree = select_edges(topology)
    edges, clients = build_edges_with_clients(
        args,
        edges,
        devices,
        config,
        site,
        clients_override=clients_override,
        node_names=topology.node_names,
    )
    layout_mode = getattr(args, "svg_layout_mode", "physical")
    effective_layout = "grouped" if layout_mode == "vlan" else layout_mode
    options = SvgOptions(width=args.svg_width, height=args.svg_height, layout_mode=effective_layout)

    node_types = build_node_type_map(
        devices, clients, client_mode=args.client_scope, only_unifi=args.only_unifi
    )
    node_names = build_node_names(
        devices, clients, client_mode=args.client_scope, only_unifi=args.only_unifi
    )

    groups = None
    group_order = None
    group_vlan_ids: dict[str, int] | None = None
    networks = _fetch_networks_for_wan(config, site, networks_override=networks_override)

    if layout_mode == "grouped":
        groups = group_devices_by_type(devices)
        group_order = ["gateway", "switch", "ap", "other"]
        if clients:
            groups["client"] = [mac for mac, ntype in node_types.items() if ntype == "client"]
            group_order.append("client")
    elif layout_mode == "vlan":
        vlan_names = build_vlan_names(networks) if networks else {}
        groups, group_order, group_vlan_ids = group_nodes_by_vlan(edges, vlan_names)

    if getattr(args, "collapse_clients", False):
        edges, groups, group_order = _apply_client_clustering(
            edges, node_types, layout_mode, groups, group_order, node_names=node_names
        )

    wan_info = _extract_gateway_wan_info(devices, args, networks=networks)

    if args.format == "svg-iso":
        from unifi_topology.render.svg_isometric import render_svg_isometric

        return render_svg_isometric(
            edges,
            node_types=node_types,
            node_names=node_names,
            options=options,
            theme=svg_theme,
            groups=groups,
            group_order=group_order,
            group_vlan_ids=group_vlan_ids,
            wan_info=wan_info,
        )
    return render_svg(
        edges,
        node_types=node_types,
        node_names=node_names,
        options=options,
        theme=svg_theme,
        groups=groups,
        group_order=group_order,
        group_vlan_ids=group_vlan_ids,
        wan_info=wan_info,
    )


def render_mkdocs_format(
    args: argparse.Namespace,
    *,
    devices: list[Device],
    topology: TopologyResult,
    config: Config | None,
    site: str,
    mermaid_theme: MermaidTheme,
    mock_clients: list[object] | None,
) -> str | None:
    if args.mkdocs_sidebar_legend and not args.output:
        logging.error("--mkdocs-sidebar-legend requires --output")
        return None
    if args.mkdocs_sidebar_legend:
        write_mkdocs_sidebar_assets(args.output)
    port_map = build_port_map(devices, only_unifi=args.only_unifi)
    client_ports, error_code = resolve_mkdocs_client_ports(
        args,
        devices,
        config,
        site,
        mock_clients,
    )
    if error_code is not None:
        logging.error("Mock data required for client rendering")
        return None
    dark_mermaid_theme = load_dark_mermaid_theme() if args.mkdocs_dual_theme else None
    edges, _has_tree = select_edges(topology)

    infrastructure_table = _build_infrastructure_table(args, devices, config)

    options = MkdocsRenderOptions(
        direction=args.direction,
        legend_style=resolve_legend_style(
            format_name=args.format,
            legend_style=args.legend_style,
        ),
        legend_scale=args.legend_scale,
        timestamp_zone=args.mkdocs_timestamp_zone,
        client_scope=args.client_scope,
        dual_theme=args.mkdocs_dual_theme,
        infrastructure_table=infrastructure_table,
    )
    return render_mkdocs(
        edges,
        devices,
        mermaid_theme=mermaid_theme,
        port_map=port_map,
        client_ports=client_ports,
        options=options,
        dark_mermaid_theme=dark_mermaid_theme,
        node_names=topology.node_names,
    )


def render_lldp_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None,
    mock_networks: list[object] | None = None,
) -> int:
    try:
        _raw_devices, devices = load_devices_data(
            args,
            config,
            site,
            raw_devices_override=mock_devices,
            raw_networks_override=mock_networks,
        )
    except Exception as exc:
        logging.error("Failed to load devices: %s", exc)
        return 1
    if mock_clients is None:
        if config is None:
            logging.error("Mock data required for client rendering")
            return 2
        try:
            clients = list(fetch_clients(config, site=site))
        except Exception as exc:  # noqa: BLE001
            logging.warning("Failed to fetch clients; rendering without client data: %s", exc)
            clients = []
    else:
        clients = mock_clients
    content = render_lldp_md(
        devices,
        clients=clients,
        include_ports=args.include_ports,
        show_clients=args.include_clients,
        client_mode=args.client_scope,
        only_unifi=args.only_unifi,
    )
    output_kwargs = {"format_name": args.format} if args.output else {}
    write_output(content, output_path=args.output, stdout=args.stdout, **output_kwargs)
    return 0


def render_inventory_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None = None,
    mock_networks: list[object] | None = None,
) -> int:
    try:
        _raw_devices, devices = load_devices_data(
            args,
            config,
            site,
            raw_devices_override=mock_devices,
            raw_networks_override=mock_networks,
        )
    except Exception as exc:
        logging.error("Failed to load devices: %s", exc)
        return 1
    clients: list[object] | None = None
    if args.include_clients:
        if mock_clients is not None:
            clients = mock_clients
        elif config is not None:
            try:
                clients = list(fetch_clients(config, site=site))
            except Exception as exc:  # noqa: BLE001
                logging.warning("Failed to fetch clients; rendering without client data: %s", exc)
                clients = []
        else:
            logging.warning("No client data available; rendering without clients")
    content = _build_infrastructure_table(args, devices, config, clients=clients)
    if not content:
        logging.warning("No devices found for inventory")
        content = ""
    output_kwargs = {"format_name": args.format} if args.output else {}
    write_output(content, output_path=args.output, stdout=args.stdout, **output_kwargs)
    return 0


def render_standard_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None,
    mock_networks: list[object] | None = None,
    mermaid_theme: MermaidTheme,
    svg_theme: SvgTheme,
) -> int:
    topology_result = load_topology_for_render(
        args,
        config=config,
        site=site,
        mock_devices=mock_devices,
        mock_networks=mock_networks,
    )
    if topology_result is None:
        return 1
    devices, topology = topology_result

    if args.format == "mermaid":
        content = render_mermaid_output(
            args,
            devices,
            topology,
            config,
            site,
            mermaid_theme,
            clients_override=mock_clients,
            networks_override=mock_networks,
        )
    elif args.format == "mkdocs":
        content = render_mkdocs_format(
            args,
            devices=devices,
            topology=topology,
            config=config,
            site=site,
            mermaid_theme=mermaid_theme,
            mock_clients=mock_clients,
        )
        if content is None:
            return 2
    elif args.format in {"svg", "svg-iso"}:
        content = render_svg_output(
            args,
            devices,
            topology,
            config,
            site,
            svg_theme,
            clients_override=mock_clients,
            networks_override=mock_networks,
        )
    else:
        logging.error("Unsupported format: %s", args.format)
        return 2

    output_kwargs = {"format_name": args.format} if args.output else {}
    write_output(content, output_path=args.output, stdout=args.stdout, **output_kwargs)
    return 0
