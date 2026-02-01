from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

from behave import given, then, when


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_mock_path(relative_path: str) -> Path:
    return _repo_root() / relative_path


def _output_suffix(format_name: str) -> str:
    if format_name == "mermaid":
        return "mmd"
    if format_name == "mkdocs":
        return "md"
    if format_name == "lldp-md":
        return "md"
    if format_name == "payload":
        return "json"
    return "svg"


def _cli_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if "PYTHONPATH" in env else src_path
    )
    return env


def _cli_base_command() -> list[str]:
    return [sys.executable, "-m", "unifi_network_maps.cli"]


def _apply_cli_flags(cmd: list[str], *, include_ports: bool, include_clients: bool) -> None:
    if include_ports:
        cmd.append("--include-ports")
    if include_clients:
        cmd.append("--include-clients")


def _base_cli_command(format_name: str, output_path: Path, mock_data_path: Path) -> list[str]:
    return _cli_base_command() + [
        "--mock-data",
        str(mock_data_path),
        "--format",
        format_name,
        "--output",
        str(output_path),
    ]


def _build_cli_command(
    context,
    *,
    format_name: str,
    include_ports: bool,
    include_clients: bool,
    extra_args: list[str] | None,
) -> tuple[list[str], Path]:
    output_path = context.output_dir / f"output.{_output_suffix(format_name)}"
    cmd = _base_cli_command(format_name, output_path, context.mock_data_path)
    _apply_cli_flags(cmd, include_ports=include_ports, include_clients=include_clients)
    if extra_args:
        cmd.extend(extra_args)
    return cmd, output_path


def _run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, env=_cli_env(_repo_root()))


def _record_result(context, result: subprocess.CompletedProcess[str]) -> None:
    context.last_result = result
    context.last_stdout = result.stdout
    context.last_stderr = result.stderr
    context.last_returncode = result.returncode


def _ensure_mock_arg(context, args: list[str]) -> list[str]:
    if hasattr(context, "mock_data_path") and "--mock-data" not in args:
        return args + ["--mock-data", str(context.mock_data_path)]
    return args


def _format_from_args(args: list[str]) -> str:
    if "--format" in args:
        index = args.index("--format")
        if index + 1 < len(args):
            return args[index + 1]
    return "mermaid"


def _output_path_from_args(args: list[str]) -> Path | None:
    if "--output" in args:
        index = args.index("--output")
        if index + 1 < len(args):
            return Path(args[index + 1])
    if "--generate-mock" in args:
        index = args.index("--generate-mock")
        if index + 1 < len(args):
            return Path(args[index + 1])
    return None


def _run_cli(
    context,
    *,
    format_name: str,
    include_ports: bool = False,
    include_clients: bool = False,
    extra_args: list[str] | None = None,
    allow_failure: bool = False,
) -> None:
    cmd, output_path = _build_cli_command(
        context,
        format_name=format_name,
        include_ports=include_ports,
        include_clients=include_clients,
        extra_args=extra_args,
    )
    result = _run_command(cmd)
    _record_result(context, result)
    if result.returncode != 0 and not allow_failure:
        raise AssertionError(f"CLI failed: {result.stderr.strip() or result.stdout.strip()}")
    context.output_path = output_path


@when('I run the module entrypoint with "{args}"')
def when_run_module_entrypoint(context, args: str) -> None:
    cmd = [sys.executable, "-m", "unifi_network_maps"] + shlex.split(args)
    result = _run_command(cmd)
    _record_result(context, result)
    if result.returncode != 0:
        raise AssertionError(f"Entrypoint failed: {result.stderr.strip() or result.stdout.strip()}")


@when('I run the console entrypoint with "{args}"')
def when_run_console_entrypoint(context, args: str) -> None:
    cmd = [sys.executable, "-m", "unifi_network_maps.cli"] + shlex.split(args)
    result = _run_command(cmd)
    _record_result(context, result)
    if result.returncode != 0:
        raise AssertionError(f"Entrypoint failed: {result.stderr.strip() or result.stdout.strip()}")


@given('the mock data file "{relative_path}"')
def given_mock_data_file(context, relative_path: str) -> None:
    path = _resolve_mock_path(relative_path)
    if not path.exists():
        raise AssertionError(f"Mock data file missing: {path}")
    context.mock_data_path = path


@when('I run the CLI to render "{format_name}" with ports')
def when_render_with_ports(context, format_name: str) -> None:
    _run_cli(context, format_name=format_name, include_ports=True)


@when('I run the CLI to render "{format_name}" with clients')
def when_render_with_clients(context, format_name: str) -> None:
    _run_cli(context, format_name=format_name, include_clients=True)


@when('I run the CLI to render "{format_name}" with ports and clients')
def when_render_with_ports_and_clients(context, format_name: str) -> None:
    _run_cli(context, format_name=format_name, include_ports=True, include_clients=True)


@when('I run the CLI to render "{format_name}" with defaults')
def when_render_default(context, format_name: str) -> None:
    _run_cli(context, format_name=format_name)


@when('I run the CLI to render "{format_name}" with mkdocs dual theme')
def when_render_mkdocs_dual_theme(context, format_name: str) -> None:
    _run_cli(context, format_name=format_name, extra_args=["--mkdocs-dual-theme"])


@when('I run the CLI to render "{format_name}" with mkdocs timestamp off')
def when_render_mkdocs_timestamp_off(context, format_name: str) -> None:
    _run_cli(
        context,
        format_name=format_name,
        extra_args=["--mkdocs-timestamp-zone", "off"],
    )


@when('I run the CLI to render "{format_name}" with mkdocs timestamp zone "{zone}"')
def when_render_mkdocs_timestamp_zone(context, format_name: str, zone: str) -> None:
    _run_cli(
        context,
        format_name=format_name,
        extra_args=["--mkdocs-timestamp-zone", zone],
    )


@when('I run the CLI expecting failure with args "{args}"')
def when_run_cli_expecting_failure(context, args: str) -> None:
    command_args = _ensure_mock_arg(context, shlex.split(args))
    cmd = _cli_base_command() + command_args
    result = _run_command(cmd)
    _record_result(context, result)


@when('I run the CLI with args "{args}" and output file')
def when_run_cli_with_args_and_output(context, args: str) -> None:
    command_args = _ensure_mock_arg(context, shlex.split(args))
    output_path = _output_path_from_args(command_args)
    if output_path is None:
        format_name = _format_from_args(command_args)
        output_path = context.output_dir / f"output.{_output_suffix(format_name)}"
        command_args.extend(["--output", str(output_path)])
    cmd = _cli_base_command() + command_args
    result = _run_command(cmd)
    _record_result(context, result)
    if result.returncode != 0:
        raise AssertionError(f"CLI failed: {result.stderr.strip() or result.stdout.strip()}")
    context.output_path = output_path


@when("I run the CLI to generate mock data")
def when_generate_mock_data(context) -> None:
    output_path = context.output_dir / "mock_data.json"
    cmd = _cli_base_command() + ["--generate-mock", str(output_path), "--mock-seed", "1337"]
    result = _run_command(cmd)
    _record_result(context, result)
    if result.returncode != 0:
        raise AssertionError(f"CLI failed: {result.stderr.strip() or result.stdout.strip()}")
    context.output_path = output_path


@then('the output file contains "{content}"')
def then_output_contains(context, content: str) -> None:
    if not context.output_path.exists():
        raise AssertionError(f"Output file missing: {context.output_path}")
    output_text = context.output_path.read_text()
    assert content in output_text


@then('the output file does not contain "{content}"')
def then_output_does_not_contain(context, content: str) -> None:
    if not context.output_path.exists():
        raise AssertionError(f"Output file missing: {context.output_path}")
    output_text = context.output_path.read_text()
    assert content not in output_text


@then("the output file exists")
def then_output_file_exists(context) -> None:
    if not context.output_path.exists():
        raise AssertionError(f"Output file missing: {context.output_path}")


@then("the mkdocs sidebar assets are written")
def then_mkdocs_sidebar_assets_written(context) -> None:
    assets_dir = context.output_path.parent / "assets"
    expected_files = [assets_dir / "legend.js", assets_dir / "legend.css"]
    for asset_path in expected_files:
        if not asset_path.exists():
            raise AssertionError(f"Missing asset: {asset_path}")


@then('the command fails with exit code "{code}"')
def then_command_fails_with_code(context, code: str) -> None:
    assert context.last_returncode == int(code)


@then('stderr contains "{content}"')
def then_stderr_contains(context, content: str) -> None:
    assert content in context.last_stderr


@then('stdout contains "{content}"')
def then_stdout_contains(context, content: str) -> None:
    assert content in context.last_stdout


@then('the output file starts with "{prefix}"')
def then_output_starts_with(context, prefix: str) -> None:
    if not context.output_path.exists():
        raise AssertionError(f"Output file missing: {context.output_path}")
    output_text = context.output_path.read_text()
    assert output_text.startswith(prefix)
