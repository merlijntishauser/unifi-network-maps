"""CLI argument definitions."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate network maps from UniFi LLDP data, as mermaid or SVG"
    )
    add_source_args(parser.add_argument_group("Source"))
    add_mock_args(parser.add_argument_group("Mock"))
    add_functional_args(parser.add_argument_group("Functional"))
    add_mermaid_args(parser.add_argument_group("Mermaid"))
    add_svg_args(parser.add_argument_group("SVG"))
    add_general_render_args(parser.add_argument_group("Output"))
    add_debug_args(parser.add_argument_group("Debug"))
    return parser


def add_source_args(parser: argparse._ArgumentGroup) -> None:
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


def add_mock_args(parser: argparse._ArgumentGroup) -> None:
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


def add_functional_args(parser: argparse._ArgumentGroup) -> None:
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


def add_mermaid_args(parser: argparse._ArgumentGroup) -> None:
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


def add_svg_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument("--svg-width", type=int, default=None, help="SVG width override")
    parser.add_argument("--svg-height", type=int, default=None, help="SVG height override")
    parser.add_argument("--theme-file", default=None, help="Path to theme YAML file")


def add_general_render_args(parser: argparse._ArgumentGroup) -> None:
    parser.add_argument(
        "--format",
        default="mermaid",
        choices=["mermaid", "svg", "svg-iso", "lldp-md", "mkdocs", "json"],
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


def add_debug_args(parser: argparse._ArgumentGroup) -> None:
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
