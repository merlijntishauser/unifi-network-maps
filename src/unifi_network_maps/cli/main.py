"""CLI entry point."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..adapters.config import Config
from ..adapters.unifi import fetch_clients, fetch_devices
from ..io.debug import debug_dump_devices
from ..io.export import write_output
from ..io.mock_data import load_mock_data
from ..model.topology import (
    ClientPortMap,
    Device,
    PortMap,
    TopologyResult,
    build_client_edges,
    build_client_port_map,
    build_device_index,
    build_node_type_map,
    build_port_map,
    build_topology,
    group_devices_by_type,
    normalize_devices,
)
from ..render.device_ports_md import render_device_port_overview
from ..render.lldp_md import render_lldp_md
from ..render.mermaid import render_legend, render_legend_compact, render_mermaid
from ..render.mermaid_theme import MermaidTheme
from ..render.svg import SvgOptions, render_svg
from ..render.svg_theme import SvgTheme
from ..render.theme import load_theme, resolve_themes

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
    _add_mock_args(parser.add_argument_group("Mock"))
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
    parser.add_argument(
        "--mock-data",
        default=None,
        help="Path to mock data JSON (skips UniFi API calls)",
    )


def _add_mock_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument(
        "--generate-mock",
        default=None,
        help="Write mock data JSON to the given path and exit",
    )
    parser.add_argument("--mock-seed", type=int, default=1337, help="Seed for mock generation")
    parser.add_argument(
        "--mock-switches",
        type=int,
        default=1,
        help="Number of switches to generate (default: 1)",
    )
    parser.add_argument(
        "--mock-aps",
        type=int,
        default=2,
        help="Number of access points to generate (default: 2)",
    )
    parser.add_argument(
        "--mock-wired-clients",
        type=int,
        default=2,
        help="Number of wired clients to generate (default: 2)",
    )
    parser.add_argument(
        "--mock-wireless-clients",
        type=int,
        default=2,
        help="Number of wireless clients to generate (default: 2)",
    )


def _add_functional_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument("--include-ports", action="store_true", help="Include port labels in edges")
    parser.add_argument(
        "--include-clients",
        action="store_true",
        help="Include active clients as leaf nodes",
    )
    parser.add_argument(
        "--client-scope",
        choices=["wired", "wireless", "all"],
        default="wired",
        help="Client types to include (default: wired)",
    )
    parser.add_argument(
        "--only-unifi", action="store_true", help="Only include neighbors that are UniFi devices"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable UniFi API cache reads and writes",
    )


def _add_mermaid_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument("--direction", default="TB", choices=["LR", "TB"], help="Mermaid direction")
    parser.add_argument(
        "--group-by-type",
        action="store_true",
        help="Group nodes by gateway/switch/ap in Mermaid subgraphs",
    )
    parser.add_argument(
        "--legend-scale",
        type=float,
        default=1.0,
        help="Scale legend font/link sizes for Mermaid output (default: 1.0)",
    )
    parser.add_argument(
        "--legend-style",
        default="auto",
        choices=["auto", "compact", "diagram"],
        help="Legend style (auto uses compact for mkdocs, diagram otherwise)",
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
        choices=["mermaid", "svg", "svg-iso", "lldp-md", "mkdocs"],
        help="Output format",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Wrap output in a Markdown mermaid code fence for notes tools like Obsidian",
    )
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--stdout", action="store_true", help="Write output to stdout")
    parser.add_argument(
        "--mkdocs-sidebar-legend",
        action="store_true",
        help="For mkdocs output, write sidebar legend assets next to the output file",
    )
    parser.add_argument(
        "--mkdocs-dual-theme",
        action="store_true",
        help="Render light/dark Mermaid blocks for MkDocs Material theme switching",
    )
    parser.add_argument(
        "--mkdocs-timestamp-zone",
        default="Europe/Amsterdam",
        help="Timezone for mkdocs generated timestamp (use 'off' to disable)",
    )


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


def _resolve_legend_style(args: argparse.Namespace) -> str:
    if args.legend_style == "auto":
        return "compact" if args.format == "mkdocs" else "diagram"
    return args.legend_style


def _render_legend_only(args: argparse.Namespace, mermaid_theme: MermaidTheme) -> str:
    legend_style = _resolve_legend_style(args)
    if legend_style == "compact":
        content = "# Legend\n\n" + render_legend_compact(theme=mermaid_theme)
    else:
        content = render_legend(theme=mermaid_theme, legend_scale=args.legend_scale)
    if args.markdown:
        content = f"""```mermaid
{content}```
"""
    return content


def _load_devices_data(
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


def _build_topology_data(
    args: argparse.Namespace,
    config: Config | None,
    site: str,
    *,
    include_ports: bool | None = None,
    raw_devices_override: list[object] | None = None,
) -> tuple[list[Device], list[str], TopologyResult]:
    _raw_devices, devices = _load_devices_data(
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


def _build_edges_with_clients(
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
        )
    return edges, clients


def _select_edges(topology: TopologyResult) -> tuple[list, bool]:
    if topology.tree_edges:
        return topology.tree_edges, True
    logging.warning("No gateway found for hierarchy; rendering raw edges.")
    return topology.raw_edges, False


def _render_mermaid_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: TopologyResult,
    config: Config | None,
    site: str,
    mermaid_theme: MermaidTheme,
    *,
    clients_override: list[object] | None = None,
) -> str:
    edges, _has_tree = _select_edges(topology)
    edges, clients = _build_edges_with_clients(
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
        node_types=build_node_type_map(devices, clients, client_mode=args.client_scope),
        theme=mermaid_theme,
    )
    if args.markdown:
        content = f"""```mermaid
{content}```
"""
    return content


def _render_mkdocs_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: TopologyResult,
    mermaid_theme: MermaidTheme,
    port_map: PortMap,
    client_ports: ClientPortMap | None,
    timestamp_zone: str,
    dark_mermaid_theme: MermaidTheme | None = None,
) -> str:
    edges, _has_tree = _select_edges(topology)
    clients = None
    node_types = build_node_type_map(devices, clients, client_mode=args.client_scope)
    content = render_mermaid(
        edges,
        direction=args.direction,
        node_types=node_types,
        theme=mermaid_theme,
    )
    legend_style = _resolve_legend_style(args)
    dual_theme = args.mkdocs_dual_theme and dark_mermaid_theme is not None
    legend_header = "## Legend\n\n" if legend_style != "compact" else ""
    if dual_theme and dark_mermaid_theme is not None:
        dark_content = render_mermaid(
            edges,
            direction=args.direction,
            node_types=node_types,
            theme=dark_mermaid_theme,
        )
        map_block = _mkdocs_dual_mermaid_block(content, dark_content, base_class="unifi-mermaid")
        legend_block = _mkdocs_dual_legend_block(
            legend_style,
            mermaid_theme=mermaid_theme,
            dark_mermaid_theme=dark_mermaid_theme,
            legend_scale=args.legend_scale,
        )
        dual_style = _mkdocs_dual_theme_style()
    else:
        map_block = _mkdocs_mermaid_block(content, class_name="unifi-mermaid")
        legend_block = _mkdocs_single_legend_block(
            legend_style,
            mermaid_theme=mermaid_theme,
            legend_scale=args.legend_scale,
        )
        dual_style = ""
    timestamp_line = ""
    if timestamp_zone.strip().lower() not in {"off", "none", "false"}:
        try:
            zone = ZoneInfo(timestamp_zone)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Invalid mkdocs timestamp zone '%s': %s", timestamp_zone, exc)
        else:
            generated_at = datetime.now(zone).strftime("%Y-%m-%d %H:%M:%S %Z")
            timestamp_line = f"Generated: {generated_at}\n\n"
    return (
        f"# UniFi network\n\n{timestamp_line}{dual_style}## Map\n\n{map_block}\n\n"
        f"{legend_header}{legend_block}\n\n"
        f"{render_device_port_overview(devices, port_map, client_ports=client_ports)}"
    )


def _mkdocs_mermaid_block(content: str, *, class_name: str) -> str:
    return f'<div class="{class_name}">\n```mermaid\n{content}```\n</div>'


def _mkdocs_dual_mermaid_block(
    light_content: str,
    dark_content: str,
    *,
    base_class: str,
) -> str:
    light = _mkdocs_mermaid_block(light_content, class_name=f"{base_class} {base_class}--light")
    dark = _mkdocs_mermaid_block(dark_content, class_name=f"{base_class} {base_class}--dark")
    return f"{light}\n{dark}"


def _mkdocs_single_legend_block(
    legend_style: str,
    *,
    mermaid_theme: MermaidTheme,
    legend_scale: float,
) -> str:
    if legend_style == "compact":
        return (
            '<div class="unifi-legend" data-unifi-legend>\n'
            + render_legend_compact(theme=mermaid_theme)
            + "</div>"
        )
    return "```mermaid\n" + render_legend(theme=mermaid_theme, legend_scale=legend_scale) + "```"


def _mkdocs_dual_legend_block(
    legend_style: str,
    *,
    mermaid_theme: MermaidTheme,
    dark_mermaid_theme: MermaidTheme,
    legend_scale: float,
) -> str:
    if legend_style == "compact":
        light = (
            '<div class="unifi-legend unifi-legend--light" data-unifi-legend>\n'
            + render_legend_compact(theme=mermaid_theme)
            + "</div>"
        )
        dark = (
            '<div class="unifi-legend unifi-legend--dark" data-unifi-legend>\n'
            + render_legend_compact(theme=dark_mermaid_theme)
            + "</div>"
        )
        return f"{light}\n{dark}"
    light = _mkdocs_mermaid_block(
        render_legend(theme=mermaid_theme, legend_scale=legend_scale),
        class_name="unifi-legend unifi-legend--light",
    )
    dark = _mkdocs_mermaid_block(
        render_legend(theme=dark_mermaid_theme, legend_scale=legend_scale),
        class_name="unifi-legend unifi-legend--dark",
    )
    return f"{light}\n{dark}"


def _mkdocs_dual_theme_style() -> str:
    return (
        "<style>\n"
        ".unifi-mermaid--light,.unifi-legend--light{display:none;}\n"
        ".unifi-mermaid--dark,.unifi-legend--dark{display:none;}\n"
        '[data-md-color-scheme="default"] .unifi-mermaid--light{display:block;}\n'
        '[data-md-color-scheme="default"] .unifi-legend--light{display:block;}\n'
        '[data-md-color-scheme="slate"] .unifi-mermaid--dark{display:block;}\n'
        '[data-md-color-scheme="slate"] .unifi-legend--dark{display:block;}\n'
        "</style>\n\n"
    )


def _write_mkdocs_sidebar_assets(output_path: str) -> None:
    from pathlib import Path

    output_dir = Path(output_path).resolve().parent
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "legend.js").write_text(
        (
            'document.addEventListener("DOMContentLoaded", () => {\n'
            '  const legend = document.querySelector("[data-unifi-legend]");\n'
            '  const sidebar = document.querySelector(".md-sidebar--secondary .md-sidebar__scrollwrap");\n'
            "  if (!legend || !sidebar) {\n"
            "    return;\n"
            "  }\n"
            '  const wrapper = document.createElement("div");\n'
            '  wrapper.className = "unifi-legend-sidebar";\n'
            '  const title = document.createElement("div");\n'
            '  title.className = "unifi-legend-title";\n'
            '  title.textContent = "Legend";\n'
            "  wrapper.appendChild(title);\n"
            "  wrapper.appendChild(legend.cloneNode(true));\n"
            "  sidebar.appendChild(wrapper);\n"
            '  legend.classList.add("unifi-legend-hidden");\n'
            "});\n"
        ),
        encoding="utf-8",
    )
    (assets_dir / "legend.css").write_text(
        (
            ".unifi-legend-hidden {\n"
            "  display: none;\n"
            "}\n\n"
            ".unifi-legend-sidebar {\n"
            "  margin-top: 1rem;\n"
            "  padding: 0.5rem 0.75rem;\n"
            "  border: 1px solid rgba(0, 0, 0, 0.08);\n"
            "  border-radius: 6px;\n"
            "  font-size: 0.75rem;\n"
            "}\n\n"
            ".unifi-legend-title {\n"
            "  font-weight: 600;\n"
            "  margin-bottom: 0.5rem;\n"
            "}\n\n"
            ".unifi-legend-sidebar table {\n"
            "  width: 100%;\n"
            "  border-collapse: collapse;\n"
            "}\n\n"
            ".unifi-legend-sidebar td,\n"
            ".unifi-legend-sidebar th {\n"
            "  border: 0;\n"
            "  padding: 0.15rem 0;\n"
            "}\n\n"
            ".unifi-legend-sidebar svg {\n"
            "  display: block;\n"
            "}\n"
        ),
        encoding="utf-8",
    )


def _render_svg_output(
    args: argparse.Namespace,
    devices: list[Device],
    topology: TopologyResult,
    config: Config | None,
    site: str,
    svg_theme: SvgTheme,
    *,
    clients_override: list[object] | None = None,
) -> str:
    edges, _has_tree = _select_edges(topology)
    edges, clients = _build_edges_with_clients(
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
            node_types=build_node_type_map(devices, clients, client_mode=args.client_scope),
            options=options,
            theme=svg_theme,
        )
    return render_svg(
        edges,
        node_types=build_node_type_map(devices, clients, client_mode=args.client_scope),
        options=options,
        theme=svg_theme,
    )


def _handle_generate_mock(args: argparse.Namespace) -> int | None:
    if not args.generate_mock:
        return None
    try:
        from ..io.mock_generate import MockOptions, mock_payload_json
    except ImportError as exc:
        logging.error("Faker is required for --generate-mock: %s", exc)
        return 2
    options = MockOptions(
        seed=args.mock_seed,
        switch_count=max(1, args.mock_switches),
        ap_count=max(0, args.mock_aps),
        wired_client_count=max(0, args.mock_wired_clients),
        wireless_client_count=max(0, args.mock_wireless_clients),
    )
    content = mock_payload_json(options)
    write_output(content, output_path=args.generate_mock, stdout=args.stdout)
    return 0


def _load_runtime_context(
    args: argparse.Namespace,
) -> tuple[Config | None, str, list[object] | None, list[object] | None]:
    if args.mock_data:
        try:
            mock_devices, mock_clients = load_mock_data(args.mock_data)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Failed to load mock data: {exc}") from exc
        return None, "mock", mock_devices, mock_clients
    config = _load_config(args)
    if config is None:
        raise ValueError("Config required to run")
    site = _resolve_site(args, config)
    return config, site, None, None


def _render_lldp_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None,
) -> int:
    try:
        _raw_devices, devices = _load_devices_data(
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
    )
    write_output(content, output_path=args.output, stdout=args.stdout)
    return 0


def _render_standard_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None,
    mermaid_theme: MermaidTheme,
    svg_theme: SvgTheme,
) -> int:
    topology_result = _load_topology_for_render(
        args,
        config=config,
        site=site,
        mock_devices=mock_devices,
    )
    if topology_result is None:
        return 1
    devices, topology = topology_result

    if args.format == "mermaid":
        content = _render_mermaid_output(
            args,
            devices,
            topology,
            config,
            site,
            mermaid_theme,
            clients_override=mock_clients,
        )
    elif args.format == "mkdocs":
        content = _render_mkdocs_format(
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
        content = _render_svg_output(
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

    write_output(content, output_path=args.output, stdout=args.stdout)
    return 0


def _load_topology_for_render(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
) -> tuple[list[Device], TopologyResult] | None:
    try:
        include_ports = True if args.format == "mkdocs" else None
        devices, _gateways, topology = _build_topology_data(
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


def _load_dark_mermaid_theme() -> MermaidTheme | None:
    dark_theme_path = Path(__file__).resolve().parents[1] / "assets" / "themes" / "dark.yaml"
    try:
        dark_theme, _ = load_theme(dark_theme_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load dark theme: %s", exc)
        return None
    return dark_theme


def _resolve_mkdocs_client_ports(
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
    client_ports = build_client_port_map(devices, clients, client_mode=args.client_scope)
    return client_ports, None


def _render_mkdocs_format(
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
        _write_mkdocs_sidebar_assets(args.output)
    port_map = build_port_map(devices, only_unifi=args.only_unifi)
    client_ports, error_code = _resolve_mkdocs_client_ports(
        args,
        devices,
        config,
        site,
        mock_clients,
    )
    if error_code is not None:
        logging.error("Mock data required for client rendering")
        return None
    dark_mermaid_theme = _load_dark_mermaid_theme() if args.mkdocs_dual_theme else None
    return _render_mkdocs_output(
        args,
        devices,
        topology,
        mermaid_theme,
        port_map,
        client_ports,
        args.mkdocs_timestamp_zone,
        dark_mermaid_theme,
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args(argv)
    mock_result = _handle_generate_mock(args)
    if mock_result is not None:
        return mock_result
    try:
        config, site, mock_devices, mock_clients = _load_runtime_context(args)
    except ValueError as exc:
        logging.error(str(exc))
        return 2
    mermaid_theme, svg_theme = resolve_themes(args.theme_file)

    if args.legend_only:
        content = _render_legend_only(args, mermaid_theme)
        write_output(content, output_path=args.output, stdout=args.stdout)
        return 0

    if args.format == "lldp-md":
        return _render_lldp_format(
            args,
            config=config,
            site=site,
            mock_devices=mock_devices,
            mock_clients=mock_clients,
        )

    return _render_standard_format(
        args,
        config=config,
        site=site,
        mock_devices=mock_devices,
        mock_clients=mock_clients,
        mermaid_theme=mermaid_theme,
        svg_theme=svg_theme,
    )


if __name__ == "__main__":
    raise SystemExit(main())
