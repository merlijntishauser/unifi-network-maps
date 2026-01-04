"""CLI entry point."""

from __future__ import annotations

import argparse
import logging

from ..adapters.config import Config
from ..adapters.unifi import fetch_clients, fetch_devices
from ..io.debug import debug_dump_devices
from ..io.export import write_output
from ..model.topology import (
    Device,
    build_client_edges,
    build_device_index,
    build_node_type_map,
    build_topology,
    group_devices_by_type,
    normalize_devices,
)
from ..render.lldp_md import render_lldp_md
from ..render.mermaid import render_legend, render_mermaid
from ..render.mermaid_theme import MermaidTheme
from ..render.svg import SvgOptions, render_svg
from ..render.svg_theme import SvgTheme
from ..render.theme import resolve_themes

logger = logging.getLogger(__name__)


def _load_dotenv(env_file: str | None = None) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.info("python-dotenv not installed; skipping .env loading")
        return
    load_dotenv(dotenv_path=env_file) if env_file else load_dotenv()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate network maps from UniFi LLDP data, as mermaid or SVG"
    )
    _add_source_args(parser.add_argument_group("Source"))
    _add_functional_args(parser.add_argument_group("Functional"))
    _add_mermaid_args(parser.add_argument_group("Mermaid"))
    _add_svg_args(parser.add_argument_group("SVG"))
    _add_general_render_args(parser.add_argument_group("Output"))
    _add_debug_args(parser.add_argument_group("Debug"))
    return parser


def _add_source_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument("--site", default=None, help="UniFi site name (overrides UNIFI_SITE)")
    parser.add_argument(
        "--env-file",
        default=None,
        help="Path to .env file (overrides default .env discovery)",
    )


def _add_functional_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument("--include-ports", action="store_true", help="Include port labels in edges")
    parser.add_argument(
        "--include-clients",
        action="store_true",
        help="Include active clients as leaf nodes",
    )
    parser.add_argument(
        "--only-unifi", action="store_true", help="Only include neighbors that are UniFi devices"
    )


def _add_mermaid_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument("--direction", default="TB", choices=["LR", "TB"], help="Mermaid direction")
    parser.add_argument(
        "--group-by-type",
        action="store_true",
        help="Group nodes by gateway/switch/ap in Mermaid subgraphs",
    )
    parser.add_argument(
        "--legend-only",
        action="store_true",
        help="Render only the legend as a separate Mermaid graph",
    )


def _add_svg_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument("--svg-width", type=int, default=None, help="SVG width override")
    parser.add_argument("--svg-height", type=int, default=None, help="SVG height override")
    parser.add_argument("--theme-file", default=None, help="Path to theme YAML file")


def _add_general_render_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument(
        "--format",
        default="mermaid",
        choices=["mermaid", "svg", "svg-iso", "lldp-md"],
        help="Output format",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Wrap output in a Markdown mermaid code fence for notes tools like Obsidian",
    )
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--stdout", action="store_true", help="Write output to stdout")


def _add_debug_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument(
        "--debug-dump",
        action="store_true",
        help="Dump gateway and sample device data to stderr for debugging",
    )
    parser.add_argument(
        "--debug-sample",
        type=int,
        default=2,
        help="Number of non-gateway devices to include in debug dump (default: 2)",
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = _build_parser()
    return parser.parse_args(argv)


def _load_config(args: argparse.Namespace) -> Config | None:
    try:
        _load_dotenv(args.env_file)
        return Config.from_env(env_file=args.env_file)
    except ValueError as exc:
        logging.error(str(exc))
        return None


def _resolve_site(args: argparse.Namespace, config: Config) -> str:
    return args.site or config.site


def _render_legend_only(args: argparse.Namespace, mermaid_theme: MermaidTheme) -> str:
    content = render_legend(theme=mermaid_theme)
    if args.markdown:
        content = f"""```mermaid
{content}```
"""
    return content


def _load_devices_data(
    args: argparse.Namespace, config: Config, site: str
) -> tuple[list[object], list[Device]]:
    raw_devices = list(fetch_devices(config, site=site, detailed=True))
    devices = normalize_devices(raw_devices)
    if args.debug_dump:
        debug_dump_devices(raw_devices, devices, sample_count=max(0, args.debug_sample))
    return raw_devices, devices


def _build_topology_data(
    args: argparse.Namespace, config: Config, site: str
) -> tuple[list[Device], list[str], object]:
    _raw_devices, devices = _load_devices_data(args, config, site)
    groups_for_rank = group_devices_by_type(devices)
    gateways = groups_for_rank.get("gateway", [])
    topology = build_topology(
        devices,
        include_ports=args.include_ports,
        only_unifi=args.only_unifi,
        gateways=gateways,
    )
    return devices, gateways, topology


def _build_edges_with_clients(
    args: argparse.Namespace,
    edges: list,
    devices: list[Device],
    config: Config,
    site: str,
) -> tuple[list, list | None]:
    clients = None
    if args.include_clients:
        clients = list(fetch_clients(config, site=site))
        device_index = build_device_index(devices)
        edges = edges + build_client_edges(clients, device_index, include_ports=args.include_ports)
    return edges, clients


def _select_edges(topology: object) -> tuple[list, bool]:
    if topology.tree_edges:
        return topology.tree_edges, True
    logging.warning("No gateway found for hierarchy; rendering raw edges.")
    return topology.raw_edges, False


def _render_mermaid_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: object,
    config: Config,
    site: str,
    mermaid_theme: MermaidTheme,
) -> str:
    edges, _has_tree = _select_edges(topology)
    edges, clients = _build_edges_with_clients(args, edges, devices, config, site)
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
        node_types=build_node_type_map(devices, clients),
        theme=mermaid_theme,
    )
    if args.markdown:
        content = f"""```mermaid
{content}```
"""
    return content


def _render_svg_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: object,
    config: Config,
    site: str,
    svg_theme: SvgTheme,
) -> str:
    edges, _has_tree = _select_edges(topology)
    edges, clients = _build_edges_with_clients(args, edges, devices, config, site)
    options = SvgOptions(width=args.svg_width, height=args.svg_height)
    if args.format == "svg-iso":
        from ..render.svg import render_svg_isometric

        return render_svg_isometric(
            edges,
            node_types=build_node_type_map(devices, clients),
            options=options,
            theme=svg_theme,
        )
    return render_svg(
        edges,
        node_types=build_node_type_map(devices, clients),
        options=options,
        theme=svg_theme,
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args(argv)
    config = _load_config(args)
    if config is None:
        return 2
    site = _resolve_site(args, config)
    mermaid_theme, svg_theme = resolve_themes(args.theme_file)

    if args.legend_only:
        content = _render_legend_only(args, mermaid_theme)
        write_output(content, output_path=args.output, stdout=args.stdout)
        return 0

    if args.format == "lldp-md":
        try:
            _raw_devices, devices = _load_devices_data(args, config, site)
        except Exception as exc:
            logging.error("Failed to load devices: %s", exc)
            return 1
        clients = list(fetch_clients(config, site=site))
        content = render_lldp_md(
            devices,
            clients=clients,
            include_ports=args.include_ports,
            show_clients=args.include_clients,
        )
        write_output(content, output_path=args.output, stdout=args.stdout)
        return 0

    try:
        devices, _gateways, topology = _build_topology_data(args, config, site)
    except Exception as exc:
        logging.error("Failed to build topology: %s", exc)
        return 1

    if args.format == "mermaid":
        content = _render_mermaid_output(args, devices, topology, config, site, mermaid_theme)
    elif args.format in {"svg", "svg-iso"}:
        content = _render_svg_output(args, devices, topology, config, site, svg_theme)
    else:
        logging.error("Unsupported format: %s", args.format)
        return 2

    write_output(content, output_path=args.output, stdout=args.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
