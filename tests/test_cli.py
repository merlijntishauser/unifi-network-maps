import logging

from unifi_mermaid.cli import main
from unifi_mermaid.topology import Device, Edge, TopologyResult


def test_main_returns_error_on_config_failure(monkeypatch):
    def raise_config():
        raise ValueError("missing config")

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", raise_config)
    assert main([]) == 2


def test_main_legend_outputs_markdown(monkeypatch):
    captured = {}

    def write_output(content, *, output_path, stdout):
        captured["content"] = content

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.render_legend", lambda: "graph TB\n")
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

    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda: _dummy_config())
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
    monkeypatch.setattr("unifi_mermaid.cli.Config.from_env", lambda: _dummy_config())
    monkeypatch.setattr("unifi_mermaid.cli.fetch_devices", lambda *args, **kwargs: [])
    monkeypatch.setattr("unifi_mermaid.cli.normalize_devices", lambda raw: raw)

    def raise_topology(*args, **kwargs):
        raise RuntimeError("bad topology")

    monkeypatch.setattr("unifi_mermaid.cli.build_topology", raise_topology)
    caplog.set_level(logging.ERROR)
    exit_code = main(["--stdout"])
    assert exit_code == 1


def _dummy_config():
    class DummyConfig:
        url = "https://example.local"
        site = "default"
        user = "user"
        password = "pass"
        verify_ssl = True

    return DummyConfig()
