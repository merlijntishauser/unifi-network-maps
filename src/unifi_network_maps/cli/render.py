"""CLI rendering orchestration."""

from __future__ import annotations

import argparse
import logging

from ..adapters.config import Config
from ..adapters.unifi import fetch_clients
from ..io.export import write_output
from ..io.mkdocs_assets import write_mkdocs_sidebar_assets
from ..model.topology import (
    Device,
    TopologyResult,
    build_node_type_map,
    build_port_map,
    group_devices_by_type,
)
from ..render.legend import resolve_legend_style
from ..render.lldp_md import render_lldp_md
from ..render.mermaid import render_mermaid
from ..render.mermaid_theme import MermaidTheme
from ..render.mkdocs import MkdocsRenderOptions, render_mkdocs
from ..render.svg import SvgOptions, render_svg
from ..render.svg_theme import SvgTheme
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
) -> str:
    edges, _has_tree = select_edges(topology)
    edges, clients = build_edges_with_clients(
        args,
        edges,
        devices,
        config,
        site,
        clients_override=clients_override,
    )
    groups = None
    group_order = None
    if args.group_by_type:
        groups = group_devices_by_type(devices)
        group_order = ["gateway", "switch", "ap", "other"]
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
        theme=mermaid_theme,
    )
    if args.markdown:
        content = f"""```mermaid
{content}```
"""
    return content


def render_svg_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: TopologyResult,
    config: Config | None,
    site: str,
    svg_theme: SvgTheme,
    *,
    clients_override: list[object] | None = None,
) -> str:
    edges, _has_tree = select_edges(topology)
    edges, clients = build_edges_with_clients(
        args,
        edges,
        devices,
        config,
        site,
        clients_override=clients_override,
    )
    options = SvgOptions(width=args.svg_width, height=args.svg_height)
    if args.format == "svg-iso":
        from ..render.svg import render_svg_isometric

        return render_svg_isometric(
            edges,
            node_types=build_node_type_map(
                devices,
                clients,
                client_mode=args.client_scope,
                only_unifi=args.only_unifi,
            ),
            options=options,
            theme=svg_theme,
        )
    return render_svg(
        edges,
        node_types=build_node_type_map(
            devices,
            clients,
            client_mode=args.client_scope,
            only_unifi=args.only_unifi,
        ),
        options=options,
        theme=svg_theme,
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
    )
    return render_mkdocs(
        edges,
        devices,
        mermaid_theme=mermaid_theme,
        port_map=port_map,
        client_ports=client_ports,
        options=options,
        dark_mermaid_theme=dark_mermaid_theme,
    )


def render_lldp_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None,
) -> int:
    try:
        _raw_devices, devices = load_devices_data(
            args,
            config,
            site,
            raw_devices_override=mock_devices,
        )
    except Exception as exc:
        logging.error("Failed to load devices: %s", exc)
        return 1
    if mock_clients is None:
        if config is None:
            logging.error("Mock data required for client rendering")
            return 2
        clients = list(fetch_clients(config, site=site))
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


def render_standard_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None,
    mermaid_theme: MermaidTheme,
    svg_theme: SvgTheme,
) -> int:
    topology_result = load_topology_for_render(
        args,
        config=config,
        site=site,
        mock_devices=mock_devices,
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
        )
    else:
        logging.error("Unsupported format: %s", args.format)
        return 2

    output_kwargs = {"format_name": args.format} if args.output else {}
    write_output(content, output_path=args.output, stdout=args.stdout, **output_kwargs)
    return 0
