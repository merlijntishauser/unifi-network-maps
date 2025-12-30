"""CLI entry point."""

from __future__ import annotations

import argparse
import logging

from .config import Config
from .export import write_output
from .mermaid import render_mermaid
from .topology import (
    build_edges,
    build_rank_edges_by_topology,
    build_rank_edges_by_type,
    group_devices_by_type,
)
from .unifi import fetch_devices


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
    parser.add_argument("--direction", default="LR", choices=["LR", "TB"], help="Mermaid direction")
    parser.add_argument(
        "--group-by-type",
        action="store_true",
        help="Group nodes by gateway/switch/ap in Mermaid subgraphs",
    )
    parser.add_argument(
        "--hierarchy",
        action="store_true",
        help="Force gateway -> switches -> APs ordering (implies --group-by-type, uses TB layout)",
    )
    parser.add_argument(
        "--rank-mode",
        default="none",
        choices=["none", "type", "topology"],
        help="Optional ranking: type for gateway/switch/ap, topology for LLDP hop distance",
    )
    parser.add_argument("--stdout", action="store_true", help="Write output to stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = Config.from_env()
    except ValueError as exc:
        logging.error(str(exc))
        return 2

    site = args.site or config.site

    try:
        devices = list(fetch_devices(config, site=site, detailed=True))
        edges = build_edges(devices, include_ports=args.include_ports, only_unifi=args.only_unifi)
    except Exception as exc:
        logging.error("Failed to build topology: %s", exc)
        return 1

    if args.format == "mermaid":
        groups = None
        group_order = None
        direction = args.direction
        rank_mode = args.rank_mode
        if args.hierarchy:
            rank_mode = "type"
        if args.group_by_type or args.hierarchy or rank_mode == "type":
            groups = group_devices_by_type(devices)
            group_order = ["gateway", "switch", "ap", "other"]
        if args.hierarchy:
            direction = "TB"
        rank_edges = None
        if rank_mode == "type" and groups:
            rank_edges = build_rank_edges_by_type(groups, group_order or [])
            direction = "TB"
        elif rank_mode == "topology":
            if groups is None:
                groups = group_devices_by_type(devices)
            gateways = groups.get("gateway", [])
            rank_edges = build_rank_edges_by_topology(edges, gateways)
            direction = "TB"
        content = render_mermaid(
            edges,
            direction=direction,
            groups=groups,
            group_order=group_order,
            rank_edges=rank_edges,
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
