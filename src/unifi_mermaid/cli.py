"""CLI entry point."""

from __future__ import annotations

import argparse
import json
import logging

from .config import Config
from .export import write_output
from .mermaid import render_mermaid
from .topology import build_topology, group_devices_by_type, normalize_devices
from .unifi import fetch_devices

logger = logging.getLogger(__name__)


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
        config = Config.from_env()
    except ValueError as exc:
        logging.error(str(exc))
        return 2

    site = args.site or config.site

    try:
        raw_devices = list(fetch_devices(config, site=site, detailed=True))
        devices = normalize_devices(raw_devices)
        if args.debug_dump:
            _debug_dump_devices(raw_devices, devices, sample_count=max(0, args.debug_sample))
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


def _device_to_dict(device: object) -> dict:
    if hasattr(device, "to_dict"):
        return device.to_dict()
    if hasattr(device, "__dict__"):
        return dict(device.__dict__)
    return {"repr": repr(device)}


def _debug_dump_devices(
    raw_devices: list[object], normalized: list[object], *, sample_count: int
) -> None:
    name_to_device = {}
    for device in raw_devices:
        name = getattr(device, "name", None)
        if name:
            name_to_device[name] = device

    groups = group_devices_by_type(normalized)
    gateways = groups.get("gateway", [])
    samples = []
    for group in ("switch", "ap", "other"):
        for name in groups.get(group, []):
            if name not in gateways:
                samples.append(name)
            if len(samples) >= sample_count:
                break
        if len(samples) >= sample_count:
            break

    selected_names = gateways[:1] + samples
    payload = []
    for name in selected_names:
        device = name_to_device.get(name)
        if device is None:
            continue
        payload.append({"name": name, "data": _device_to_dict(device)})

    logger.info("Debug dump devices: %s", json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
