from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from behave import given, then, when


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cli_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if "PYTHONPATH" in env else src_path
    )
    return env


def _run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, env=_cli_env(_repo_root()))


@given('a Home Assistant output directory "{path}"')
def given_ha_output_directory(context, path: str) -> None:
    context.ha_output_dir = _repo_root() / path
    context.ha_output_dir.mkdir(parents=True, exist_ok=True)


@given('Home Assistant mock data file "{path}"')
def given_ha_mock_data_file(context, path: str) -> None:
    mock_path = _repo_root() / path
    if not mock_path.exists():
        raise AssertionError(f"Mock data file missing: {mock_path}")
    context.ha_mock_path = mock_path


@when('I run the Home Assistant export with args "{args}"')
def when_run_ha_export(context, args: str) -> None:
    cmd = [
        sys.executable,
        "-m",
        "unifi_network_maps.cli",
        "--mock-data",
        str(context.ha_mock_path),
    ] + shlex.split(args)
    result = _run_command(cmd)
    context.ha_result = result
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip() or result.stdout.strip())


@then('the Home Assistant output contains file "{filename}"')
def then_ha_output_contains_file(context, filename: str) -> None:
    path = context.ha_output_dir / filename
    if not path.exists():
        raise AssertionError(f"Missing HA output: {path}")


@then('the Home Assistant JSON contains keys "{keys}"')
def then_ha_json_contains_keys(context, keys: str) -> None:
    payload = _load_ha_json(context)
    for key in [item.strip() for item in keys.split(",")]:
        assert key in payload


@then('the Home Assistant JSON ports include "{keys}"')
def then_ha_json_ports_include(context, keys: str) -> None:
    payload = _load_ha_json(context)
    ports = payload.get("ports", [])
    if not ports:
        raise AssertionError("No ports found in HA JSON")
    required = [item.strip() for item in keys.split(",")]
    for key in required:
        assert key in ports[0]


@then('the Home Assistant JSON clients include "{keys}"')
def then_ha_json_clients_include(context, keys: str) -> None:
    payload = _load_ha_json(context)
    clients = payload.get("clients", [])
    if not clients:
        raise AssertionError("No clients found in HA JSON")
    required = [item.strip() for item in keys.split(",")]
    for key in required:
        assert key in clients[0]


@then('the Home Assistant JSON does not contain "{value}"')
def then_ha_json_excludes(context, value: str) -> None:
    json_text = (context.ha_output_dir / "network.json").read_text(encoding="utf-8")
    assert value not in json_text


@then('the Home Assistant Lovelace config contains "{content}"')
def then_ha_lovelace_contains(context, content: str) -> None:
    config_text = (context.ha_output_dir / "lovelace.yaml").read_text(encoding="utf-8")
    assert content in config_text


@then('the Home Assistant SVG contains "{content}"')
def then_ha_svg_contains(context, content: str) -> None:
    svg_text = (context.ha_output_dir / "network.svg").read_text(encoding="utf-8")
    assert content in svg_text


def _load_ha_json(context) -> dict[str, object]:
    json_text = (context.ha_output_dir / "network.json").read_text(encoding="utf-8")
    return json.loads(json_text)
