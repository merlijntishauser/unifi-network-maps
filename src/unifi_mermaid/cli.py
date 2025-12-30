"""CLI entry point."""

from __future__ import annotations

import argparse
import logging

from .config import Config
from .debug import debug_dump_devices
from .export import write_output
from .mermaid import render_mermaid
from .topology import (
    build_client_edges,
    build_device_index,
    build_topology,
    group_devices_by_type,
    normalize_devices,
)
from .unifi import fetch_clients, fetch_devices

logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.info("python-dotenv not installed; skipping .env loading")
        return
    load_dotenv()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Mermaid network maps from UniFi LLDP data"
    )
    parser.add_argument("--site", default=None, help="UniFi site name (overrides UNIFI_SITE)")
    parser.add_argument("--format", default="mermaid", choices=["mermaid"], help="Output format")
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Wrap output in a Markdown mermaid code fence for notes tools like Obsidian",
    )
    parser.add_argument("--output", default=None, help="Output file path")
    parser.add_argument("--include-ports", action="store_true", help="Include port labels in edges")
    parser.add_argument(
        "--only-unifi", action="store_true", help="Only include neighbors that are UniFi devices"
    )
    parser.add_argument("--direction", default="TB", choices=["LR", "TB"], help="Mermaid direction")
    parser.add_argument(
        "--group-by-type",
        action="store_true",
        help="Group nodes by gateway/switch/ap in Mermaid subgraphs",
    )
    parser.add_argument(
        "--include-clients",
        action="store_true",
        help="Include active clients as leaf nodes",
    )
    parser.add_argument("--stdout", action="store_true", help="Write output to stdout")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        _load_dotenv()
        config = Config.from_env()
    except ValueError as exc:
        logging.error(str(exc))
        return 2

    site = args.site or config.site

    try:
        raw_devices = list(fetch_devices(config, site=site, detailed=True))
        devices = normalize_devices(raw_devices)
        if args.debug_dump:
            debug_dump_devices(raw_devices, devices, sample_count=max(0, args.debug_sample))
        groups_for_rank = group_devices_by_type(devices)
        gateways = groups_for_rank.get("gateway", [])
        topology = build_topology(
            devices,
            include_ports=args.include_ports,
            only_unifi=args.only_unifi,
            gateways=gateways,
        )
    except Exception as exc:
        logging.error("Failed to build topology: %s", exc)
        return 1

    if args.format == "mermaid":
        groups = None
        group_order = None
        direction = args.direction
        if topology.tree_edges:
            edges = topology.tree_edges
        else:
            edges = topology.raw_edges
            logging.warning("No gateway found for hierarchy; rendering raw edges.")
        if args.include_clients:
            clients = list(fetch_clients(config, site=site))
            device_index = build_device_index(devices)
            edges = edges + build_client_edges(clients, device_index)
        if args.group_by_type:
            groups = groups_for_rank
            group_order = ["gateway", "switch", "ap", "other"]
        content = render_mermaid(
            edges,
            direction=direction,
            groups=groups,
            group_order=group_order,
        )
    else:
        logging.error("Unsupported format: %s", args.format)
        return 2

    if args.markdown:
        content = f"""```mermaid
{content}```
"""

    write_output(content, output_path=args.output, stdout=args.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
