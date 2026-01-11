"""CLI entry point."""

from __future__ import annotations

import argparse
import logging

from ..adapters.config import Config
from ..io.export import write_output
from ..io.mock_data import load_mock_data
from ..render.legend import render_legend_only, resolve_legend_style
from ..render.theme import resolve_themes
from .args import build_parser
from .render import render_lldp_format, render_standard_format

logger = logging.getLogger(__name__)


def _load_dotenv(env_file: str | None = None) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.info("python-dotenv not installed; skipping .env loading")
        return
    load_dotenv(dotenv_path=env_file) if env_file else load_dotenv()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = build_parser()
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


def _handle_generate_mock(args: argparse.Namespace) -> int | None:
    if not args.generate_mock:
        return None
    try:
        from ..model.mock import MockOptions, mock_payload_json
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
        write_output(content, output_path=args.output, stdout=args.stdout)
        return 0

    if args.format == "lldp-md":
        return render_lldp_format(
            args,
            config=config,
            site=site,
            mock_devices=mock_devices,
            mock_clients=mock_clients,
        )

    return render_standard_format(
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
