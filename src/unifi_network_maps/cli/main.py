"""CLI entry point."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import yaml
from unifi_topology.adapters.config import Config
from unifi_topology.adapters.unifi import fetch_payload
from unifi_topology.model.vlans import build_vlan_info, normalize_networks

from ..io.export import write_output
from ..io.mock_data import load_mock_data, load_mock_payload
from ..io.paths import (
    resolve_env_file,
    resolve_mock_data_path,
    resolve_output_path,
    resolve_theme_path,
)
from ..render.legend import render_legend_only, resolve_legend_style
from ..render.theme import resolve_themes
from .args import build_parser
from .render import render_inventory_format, render_lldp_format, render_standard_format

logger = logging.getLogger(__name__)


def _load_dotenv(env_file: str | Path | None = None) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.info("python-dotenv not installed; skipping .env loading")
        return
    load_dotenv(dotenv_path=env_file) if env_file else load_dotenv()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def _validate_paths(args: argparse.Namespace) -> bool:
    try:
        if args.env_file:
            resolve_env_file(args.env_file)
        if args.mock_data:
            resolve_mock_data_path(args.mock_data, require_exists=False)
        if args.theme_file:
            resolve_theme_path(args.theme_file, require_exists=False)
        if args.generate_mock:
            resolve_output_path(args.generate_mock, format_name="mock")
        if args.output:
            resolve_output_path(args.output, format_name=args.format)
    except ValueError as exc:
        logging.error(str(exc))
        return False
    return True


def _load_config(args: argparse.Namespace) -> Config | None:
    try:
        _load_dotenv(args.env_file)
        return Config.from_env(env_file=args.env_file)
    except ValueError as exc:
        logging.error(str(exc))
        return None


def _resolve_site(args: argparse.Namespace, config: Config) -> str:
    return args.site or config.site


def _handle_generate_mock(args: argparse.Namespace) -> int | None:
    if not args.generate_mock:
        return None
    try:
        from unifi_topology.model.mock import MockOptions, mock_payload_json
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
    output_kwargs = {"format_name": "mock"} if args.generate_mock else {}
    write_output(content, output_path=args.generate_mock, stdout=args.stdout, **output_kwargs)
    return 0


def _load_runtime_context(
    args: argparse.Namespace,
) -> tuple[Config | None, str, list[object] | None, list[object] | None, list[object] | None]:
    if args.mock_data:
        try:
            mock_devices, mock_clients, mock_networks = load_mock_data(args.mock_data)
        except (OSError, ValueError) as exc:
            raise ValueError(f"Failed to load mock data: {exc}") from exc
        return None, "mock", mock_devices, mock_clients, mock_networks
    config = _load_config(args)
    if config is None:
        raise ValueError("Config required to run")
    site = _resolve_site(args, config)
    return config, site, None, None, None


def _handle_device_only_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
    mock_devices: list[object] | None,
    mock_clients: list[object] | None,
    mock_networks: list[object] | None,
) -> int | None:
    if args.format == "inventory":
        return render_inventory_format(
            args,
            config=config,
            site=site,
            mock_devices=mock_devices,
            mock_clients=mock_clients,
            mock_networks=mock_networks,
        )
    if args.format == "lldp-md":
        return render_lldp_format(
            args,
            config=config,
            site=site,
            mock_devices=mock_devices,
            mock_clients=mock_clients,
            mock_networks=mock_networks,
        )
    return None


def _handle_json_format(
    args: argparse.Namespace,
    *,
    config: Config | None,
    site: str,
) -> int | None:
    if args.format != "json":
        return None
    payload: dict[str, list[object] | list[dict[str, object]]]
    if args.mock_data:
        payload = load_mock_payload(args.mock_data)
        if not args.include_clients:
            payload["clients"] = []
        networks = normalize_networks(payload.get("networks", []))
        payload["networks"] = networks
        payload["vlan_info"] = build_vlan_info(payload.get("clients", []), networks)
    else:
        if config is None:
            logging.error("Config required to run")
            return 2
        payload = fetch_payload(
            config,
            site=site,
            include_clients=args.include_clients,
            use_cache=not args.no_cache,
        )
    content = json.dumps(payload, indent=2, sort_keys=True)
    output_kwargs = {"format_name": args.format} if args.output else {}
    write_output(content, output_path=args.output, stdout=args.stdout, **output_kwargs)
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args(argv)
    if not _validate_paths(args):
        return 2
    mock_result = _handle_generate_mock(args)
    if mock_result is not None:
        return mock_result
    try:
        config, site, mock_devices, mock_clients, mock_networks = _load_runtime_context(args)
    except ValueError as exc:
        logging.error(str(exc))
        return 2
    for early_result in (
        _handle_json_format(args, config=config, site=site),
        _handle_device_only_format(
            args,
            config=config,
            site=site,
            mock_devices=mock_devices,
            mock_clients=mock_clients,
            mock_networks=mock_networks,
        ),
    ):
        if early_result is not None:
            return early_result
    try:
        mermaid_theme, svg_theme = resolve_themes(
            theme_name=args.theme,
            theme_file=args.theme_file,
        )
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        logging.error("Failed to load theme: %s", exc)
        return 2

    # Apply CLI icon-set override if specified
    if args.icon_set:
        from dataclasses import replace

        svg_theme = replace(svg_theme, icon_set=args.icon_set)

    if args.legend_only:
        legend_style = resolve_legend_style(
            format_name=args.format,
            legend_style=args.legend_style,
        )
        content = render_legend_only(
            legend_style=legend_style,
            legend_scale=args.legend_scale,
            markdown=args.markdown,
            theme=mermaid_theme,
        )
        output_kwargs = {"format_name": args.format} if args.output else {}
        write_output(content, output_path=args.output, stdout=args.stdout, **output_kwargs)
        return 0

    return render_standard_format(
        args,
        config=config,
        site=site,
        mock_devices=mock_devices,
        mock_clients=mock_clients,
        mock_networks=mock_networks,
        mermaid_theme=mermaid_theme,
        svg_theme=svg_theme,
    )


if __name__ == "__main__":
    raise SystemExit(main())
