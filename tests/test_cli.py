import builtins
import importlib
import json
import logging
import runpy
import sys

import pytest

from unifi_network_maps.model.topology import Device, Edge, TopologyResult

cli_module = importlib.import_module("unifi_network_maps.cli.main")
runtime_module = importlib.import_module("unifi_network_maps.cli.runtime")
render_module = importlib.import_module("unifi_network_maps.cli.render")
mkdocs_module = importlib.import_module("unifi_network_maps.render.mkdocs")
legend_module = importlib.import_module("unifi_network_maps.render.legend")
main = cli_module.main


def test_main_returns_error_on_config_failure(monkeypatch):
    def raise_config(**_kwargs):
        raise ValueError("missing config")

    monkeypatch.setattr(cli_module.Config, "from_env", raise_config)
    assert main([]) == 2


def test_main_generate_mock_skips_config(monkeypatch, tmp_path):
    def fail_config(**_kwargs):
        raise AssertionError("Config should not load for mock generation")

    monkeypatch.setattr(cli_module.Config, "from_env", fail_config)
    output_path = tmp_path / "mock.json"
    assert main(["--generate-mock", str(output_path)]) == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert "devices" in payload


def test_main_mock_data_skips_config(monkeypatch, tmp_path):
    payload = {
        "devices": [
            {
                "name": "Gateway",
                "model_name": "",
                "model": "",
                "mac": "aa:bb",
                "ip": "",
                "type": "udm",
                "lldp_info": [],
            }
        ],
        "clients": [],
    }
    mock_path = tmp_path / "mock.json"
    mock_path.write_text(json.dumps(payload), encoding="utf-8")

    def fail_config(**_kwargs):
        raise AssertionError("Config should not load for mock data")

    monkeypatch.setattr(cli_module.Config, "from_env", fail_config)
    monkeypatch.setattr(render_module, "render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    assert main(["--mock-data", str(mock_path), "--stdout"]) == 0


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

    monkeypatch.setattr(cli_module.Config, "from_env", fake_from_env)
    monkeypatch.setattr(legend_module, "render_legend", lambda **_kwargs: "graph TB\n")
    monkeypatch.setattr(cli_module, "write_output", lambda *args, **kwargs: None)

    assert main(["--env-file", "custom.env", "--legend-only", "--stdout"]) == 0
    assert captured["env_file"] == "custom.env"


def test_main_legend_outputs_markdown(monkeypatch):
    captured = {}

    def write_output(content, *, output_path, stdout):
        captured["content"] = content

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(legend_module, "render_legend", lambda **_kwargs: "graph TB\n")
    monkeypatch.setattr(cli_module, "write_output", write_output)

    main(["--legend-only", "--markdown", "--stdout"])
    assert captured["content"].startswith("```mermaid")


def test_main_mermaid_includes_wired_clients(monkeypatch):
    captured = {}
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]
    clients = [{"name": "Client", "is_wired": True, "sw_mac": "aa:bb"}]

    def fake_render_mermaid(edges, *, node_types, **kwargs):
        captured["node_types"] = node_types
        return "graph TB\n"

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        runtime_module, "group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr(runtime_module, "fetch_clients", lambda *args, **kwargs: clients)
    monkeypatch.setattr(render_module, "render_mermaid", fake_render_mermaid)
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    main(["--include-clients", "--stdout"])
    assert captured["node_types"]["Client"] == "client"


def test_main_payload_from_mock_includes_vlan_info(monkeypatch, tmp_path):
    captured = {}
    payload = {
        "devices": [
            {
                "name": "Gateway",
                "model_name": "",
                "model": "",
                "mac": "aa:bb",
                "ip": "",
                "type": "udm",
                "lldp_info": [],
            }
        ],
        "clients": [{"name": "Client A", "is_wired": True, "sw_mac": "aa:bb", "vlan": 20}],
        "networks": [
            {"name": "LAN", "vlan_enabled": False},
            {"name": "Guest", "vlan": 20, "vlan_enabled": True},
        ],
    }
    mock_path = tmp_path / "mock.json"
    mock_path.write_text(json.dumps(payload), encoding="utf-8")

    def write_output(content, *, output_path, stdout, **_kwargs):
        captured["content"] = content

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(cli_module, "write_output", write_output)

    assert (
        main(
            [
                "--mock-data",
                str(mock_path),
                "--format",
                "json",
                "--include-clients",
                "--stdout",
            ]
        )
        == 0
    )
    output = json.loads(captured["content"])
    assert "networks" in output
    assert "vlan_info" in output
    vlan_map = {entry["id"]: entry for entry in output["vlan_info"]}
    assert vlan_map[1]["client_count"] == 0
    assert vlan_map[20]["client_count"] == 1


def test_main_payload_from_mock_excludes_clients_by_default(monkeypatch, tmp_path):
    captured = {}
    payload = {
        "devices": [
            {
                "name": "Gateway",
                "model_name": "",
                "model": "",
                "mac": "aa:bb",
                "ip": "",
                "type": "udm",
                "lldp_info": [],
            }
        ],
        "clients": [{"name": "Client A", "is_wired": True, "sw_mac": "aa:bb", "vlan": 20}],
        "networks": [
            {"name": "LAN", "vlan_enabled": False},
            {"name": "Guest", "vlan": 20, "vlan_enabled": True},
        ],
    }
    mock_path = tmp_path / "mock.json"
    mock_path.write_text(json.dumps(payload), encoding="utf-8")

    def write_output(content, *, output_path, stdout, **_kwargs):
        captured["content"] = content

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(cli_module, "write_output", write_output)

    assert main(["--mock-data", str(mock_path), "--format", "json", "--stdout"]) == 0
    output = json.loads(captured["content"])
    vlan_map = {entry["id"]: entry for entry in output["vlan_info"]}
    assert vlan_map[1]["client_count"] == 0
    assert vlan_map[20]["client_count"] == 0


def test_main_logs_topology_errors(monkeypatch, caplog):
    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: [])
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)

    def raise_topology(*args, **kwargs):
        raise RuntimeError("bad topology")

    monkeypatch.setattr(runtime_module, "build_topology", raise_topology)
    caplog.set_level(logging.ERROR)
    exit_code = main(["--stdout"])
    assert exit_code == 1


def test_main_mermaid_wraps_markdown(monkeypatch):
    captured = {}
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]

    def write_output(content, *, output_path, stdout):
        captured["content"] = content

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        runtime_module, "group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr(render_module, "render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(render_module, "write_output", write_output)

    main(["--markdown", "--stdout"])
    assert captured["content"].startswith("```mermaid")


def test_main_mkdocs_includes_legend(monkeypatch):
    captured = {}
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]

    def write_output(content, *, output_path, stdout):
        captured["content"] = content

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        runtime_module, "group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr(mkdocs_module, "render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(mkdocs_module, "render_legend", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(render_module, "build_port_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(runtime_module, "build_client_port_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        mkdocs_module, "render_device_port_overview", lambda *args, **kwargs: "PORTS\n"
    )
    monkeypatch.setattr(render_module, "write_output", write_output)

    assert main(["--format", "mkdocs", "--stdout"]) == 0
    assert "unifi-legend-table" in captured["content"]
    assert "PORTS" in captured["content"]


def test_main_mkdocs_sidebar_requires_output(monkeypatch):
    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: [])
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(runtime_module, "group_devices_by_type", lambda *_: {"gateway": []})
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(raw_edges=[], tree_edges=[]),
    )
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    assert main(["--format", "mkdocs", "--mkdocs-sidebar-legend", "--stdout"]) == 2


def test_main_mkdocs_sidebar_writes_assets(monkeypatch, tmp_path):
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        runtime_module, "group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr(mkdocs_module, "render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(mkdocs_module, "render_legend", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(render_module, "build_port_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        mkdocs_module, "render_device_port_overview", lambda *args, **kwargs: "PORTS\n"
    )
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    output_path = tmp_path / "unifi-network.md"
    assert (
        main(["--format", "mkdocs", "--mkdocs-sidebar-legend", "--output", str(output_path)]) == 0
    )
    assert (tmp_path / "assets" / "legend.js").exists()
    assert (tmp_path / "assets" / "legend.css").exists()


def test_main_mkdocs_sidebar_disabled_does_not_write_assets(monkeypatch, tmp_path):
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        runtime_module, "group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr(mkdocs_module, "render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(mkdocs_module, "render_legend", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(render_module, "build_port_map", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        mkdocs_module, "render_device_port_overview", lambda *args, **kwargs: "PORTS\n"
    )
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    output_path = tmp_path / "unifi-network.md"
    assert main(["--format", "mkdocs", "--output", str(output_path)]) == 0
    assert not (tmp_path / "assets" / "legend.js").exists()


def test_main_debug_dump_uses_non_negative_sample(monkeypatch):
    captured = {}
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]

    def debug_dump(raw_devices, normalized, *, sample_count):
        captured["sample_count"] = sample_count

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(runtime_module, "debug_dump_devices", debug_dump)
    monkeypatch.setattr(
        runtime_module, "group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr(render_module, "render_mermaid", lambda *args, **kwargs: "graph TB\n")
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    main(["--debug-dump", "--debug-sample", "-5", "--stdout"])
    assert captured["sample_count"] == 0


def test_main_svg_uses_size_overrides(monkeypatch):
    captured = {}
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]

    def fake_render_svg(edges, *, node_types, options, theme=None):
        captured["width"] = options.width
        captured["height"] = options.height
        return "<svg></svg>"

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(
        runtime_module, "group_devices_by_type", lambda *_: {"gateway": ["Gateway"]}
    )
    monkeypatch.setattr(
        runtime_module,
        "build_topology",
        lambda *args, **kwargs: TopologyResult(
            raw_edges=[Edge("Gateway", "Switch")],
            tree_edges=[Edge("Gateway", "Switch")],
        ),
    )
    monkeypatch.setattr(render_module, "render_svg", fake_render_svg)
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    main(["--format", "svg", "--svg-width", "800", "--svg-height", "600", "--stdout"])
    assert captured["width"] == 800


def test_main_lldp_md_skips_topology(monkeypatch):
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]

    def explode(*_args, **_kwargs):
        raise RuntimeError("unexpected topology build")

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(render_module, "fetch_clients", lambda *args, **kwargs: [])
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(runtime_module, "build_topology", explode)
    monkeypatch.setattr(render_module, "render_lldp_md", lambda *_args, **_kwargs: "# LLDP\n")
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    assert main(["--format", "lldp-md", "--stdout"]) == 0


def test_main_lldp_md_includes_clients(monkeypatch):
    devices = [
        Device(
            name="Gateway", model_name="", model="", mac="aa:bb", ip="", type="udm", lldp_info=[]
        )
    ]
    captured = {}

    def fake_render_lldp_md(*_args, **kwargs):
        captured["clients"] = kwargs.get("clients")
        captured["show_clients"] = kwargs.get("show_clients")
        captured["client_mode"] = kwargs.get("client_mode")
        return "# LLDP\n"

    monkeypatch.setattr(cli_module.Config, "from_env", lambda **_kwargs: _dummy_config())
    monkeypatch.setattr(runtime_module, "fetch_devices", lambda *args, **kwargs: devices)
    monkeypatch.setattr(runtime_module, "normalize_devices", lambda raw: raw)
    monkeypatch.setattr(render_module, "fetch_clients", lambda *args, **kwargs: [{"name": "TV"}])
    monkeypatch.setattr(render_module, "render_lldp_md", fake_render_lldp_md)
    monkeypatch.setattr(render_module, "write_output", lambda *args, **kwargs: None)

    assert main(["--format", "lldp-md", "--include-clients", "--stdout"]) == 0
    assert captured["clients"] is not None
    assert captured["show_clients"] is True
    assert captured["client_mode"] == "wired"


def test_cli_wrapper_calls_main(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["unifi_network_maps.cli", "--help"])
    sys.modules.pop("unifi_network_maps.cli", None)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("unifi_network_maps.cli", run_name="__main__")
    assert excinfo.value.code == 0


def _dummy_config():
    class DummyConfig:
        url = "https://example.local"
        site = "default"
        user = "user"
        password = "pass"
        verify_ssl = True

    return DummyConfig()
