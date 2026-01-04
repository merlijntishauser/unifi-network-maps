import builtins
import logging
import runpy
import sys

import pytest

from unifi_mermaid import cli as cli_module
from unifi_mermaid.cli import main
from unifi_mermaid.topology import Device, Edge, TopologyResult


def test_main_returns_error_on_config_failure(monkeypatch):
    def raise_config(**_kwargs):
        raise ValueError("missing config")

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", raise_config)
    assert main([]) == 2


def test_load_dotenv_logs_when_missing(monkeypatch, caplog):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "dotenv":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    caplog.set_level(logging.INFO)
    cli_module._load_dotenv(None)
    assert "python-dotenv not installed" in caplog.text


def test_load_dotenv_passes_env_file(monkeypatch):
    captured = {}

    def fake_load_dotenv(*, dotenv_path=None):
        captured["dotenv_path"] = dotenv_path

    import types

    monkeypatch.setitem(sys.modules, "dotenv", types.SimpleNamespace(load_dotenv=fake_load_dotenv))
    cli_module._load_dotenv("custom.env")
    assert captured["dotenv_path"] == "custom.env"


def test_main_passes_env_file_to_config(monkeypatch):
    captured = {}

    def fake_from_env(*, env_file=None):
        captured["env_file"] = env_file
        return _dummy_config()

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", fake_from_env)
    monkeypatch.setattr("unifi_mermaid.cli.render_legend", lambda **_kwargs: "graph TB\n")
    monkeypatch.setattr("unifi_mermaid.cli.write_output", lambda *args, **kwargs: None)

    assert main(["--env-file", "custom.env", "--legend-only", "--stdout"]) == 0
    assert captured["env_file"] == "custom.env"


def test_main_legend_outputs_markdown(monkeypatch):
    captured = {}

    def write_output(content, *, output_path, stdout):
        captured["content"] = content

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.render_legend", lambda **_kwargs: "graph TB\n")
    monkeypatch.setattr("unifi_mermaid.cli.write_output", write_output)

    main(["--legend-only", "--markdown", "--stdout"])
    assert captured["content"].startswith("```mermaid")


def test_main_mermaid_includes_wired_clients(monkeypatch):
    captured = {}
    devices = [Device(name="Gateway", model_name="", mac="aa:bb", ip="", type="udm", lldp_info=[])]
    clients = [{"name": "Client", "is_wired": True, "sw_mac": "aa:bb"}]

    def fake_render_mermaid(edges, *, node_types, **kwargs):
        captured["node_types"] = node_types
        return "graph TB\n"

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr("unifi_mermaid.cli.normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        "unifi_mermaid.cli.group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        "unifi_mermaid.cli.build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr("unifi_mermaid.cli.fetch_clients", lambda *args, **kwargs: clients)
    monkeypatch.setattr("unifi_mermaid.cli.render_mermaid", fake_render_mermaid)
    monkeypatch.setattr("unifi_mermaid.cli.write_output", lambda *args, **kwargs: None)

    main(["--include-clients", "--stdout"])
    assert captured["node_types"]["Client"] == "client"


def test_main_logs_topology_errors(monkeypatch, caplog):
    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.fetch_devices", lambda *args, **kwargs: [])
    monkeypatch.setattr("unifi_mermaid.cli.normalize_devices", lambda raw: raw)

    def raise_topology(*args, **kwargs):
        raise RuntimeError("bad topology")

    monkeypatch.setattr("unifi_mermaid.cli.build_topology", raise_topology)
    caplog.set_level(logging.ERROR)
    exit_code = main(["--stdout"])
    assert exit_code == 1


def test_main_mermaid_wraps_markdown(monkeypatch):
    captured = {}
    devices = [Device(name="Gateway", model_name="", mac="aa:bb", ip="", type="udm", lldp_info=[])]

    def write_output(content, *, output_path, stdout):
        captured["content"] = content

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr("unifi_mermaid.cli.normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        "unifi_mermaid.cli.group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        "unifi_mermaid.cli.build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr("unifi_mermaid.cli.render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr("unifi_mermaid.cli.write_output", write_output)

    main(["--markdown", "--stdout"])
    assert captured["content"].startswith("```mermaid")


def test_main_debug_dump_uses_non_negative_sample(monkeypatch):
    captured = {}
    devices = [Device(name="Gateway", model_name="", mac="aa:bb", ip="", type="udm", lldp_info=[])]

    def debug_dump(raw_devices, normalized, *, sample_count):
        captured["sample_count"] = sample_count

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr("unifi_mermaid.cli.normalize_devices", lambda raw: raw)
    monkeypatch.setattr("unifi_mermaid.cli.debug_dump_devices", debug_dump)
    monkeypatch.setattr(
        "unifi_mermaid.cli.group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        "unifi_mermaid.cli.build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr("unifi_mermaid.cli.render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr("unifi_mermaid.cli.write_output", lambda *args, **kwargs: None)

    main(["--debug-dump", "--debug-sample", "-5", "--stdout"])
    assert captured["sample_count"] == 0


def test_main_svg_uses_size_overrides(monkeypatch):
    captured = {}
    devices = [Device(name="Gateway", model_name="", mac="aa:bb", ip="", type="udm", lldp_info=[])]

    def fake_render_svg(edges, *, node_types, options, theme=None):
        captured["width"] = options.width
        captured["height"] = options.height
        return "<svg></svg>"

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr("unifi_mermaid.cli.normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        "unifi_mermaid.cli.group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        "unifi_mermaid.cli.build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr("unifi_mermaid.cli.render_svg", fake_render_svg)
    monkeypatch.setattr("unifi_mermaid.cli.write_output", lambda *args, **kwargs: None)

    main(["--format", "svg", "--svg-width", "800", "--svg-height", "600", "--stdout"])
    assert captured["width"] == 800


def test_cli_wrapper_calls_main(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["unifi_mermaid.cli", "--help"])
    sys.modules.pop("unifi_mermaid.cli", None)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("unifi_mermaid.cli", run_name="__main__")
    assert excinfo.value.code == 0


def _dummy_config():
    class DummyConfig:
        url = "https://example.local"
        site = "default"
        user = "user"
        password = "pass"
        verify_ssl = True

    return DummyConfig()
