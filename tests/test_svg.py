import re
from pathlib import Path

import unifi_network_maps.render.svg as svg_module
from unifi_network_maps.model.topology import Edge


def test_render_svg_outputs_svg_root():
    output = svg_module.render_svg([Edge("A", "B")], node_types={"A": "gateway", "B": "switch"})
    assert output.startswith("<svg")


def test_render_svg_respects_size_override():
    output = svg_module.render_svg(
        [Edge("A", "B")],
        node_types={"A": "gateway", "B": "switch"},
        options=svg_module.SvgOptions(width=800, height=600),
    )
    assert 'width="800"' in output


def test_render_svg_escapes_edge_labels():
    output = svg_module.render_svg(
        [Edge("A", "B", label="Port 1 <-> Port 2")],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert "&lt;-&gt;" in output


def test_render_svg_renders_poe_icon():
    output = svg_module.render_svg(
        [Edge("A", "B", poe=True)],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert "⚡" in output


def test_render_svg_dashes_wireless_links():
    output = svg_module.render_svg(
        [Edge("A", "B", wireless=True)],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert 'stroke-dasharray="6 4"' in output


def test_render_svg_adds_elbow_for_vertical_links():
    output = svg_module.render_svg(
        [Edge("Root", "Child")],
        node_types={"Root": "gateway", "Child": "switch"},
    )
    match = re.search(r'<path d="([^"]+)"', output)
    assert match is not None
    coords = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", match.group(1))]
    x_values = {round(x, 2) for x in coords[0::2]}
    assert len(x_values) > 1


def test_render_svg_compacts_device_labels():
    output = svg_module.render_svg(
        [Edge("A", "B", label="Switch A: Port 2 <-> Switch B: Port 5")],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert 'class="node-port"' in output
    assert "Switch A Port 2" in output
    assert ">5</tspan>" in output


def test_render_svg_orders_upstream_label():
    output = svg_module.render_svg(
        [Edge("Parent", "Child", label="Child: Port 1 <-> Parent: Port 2")],
        node_types={"Parent": "switch", "Child": "switch"},
    )
    assert "Parent Port 2 &lt;-&gt; Port 1" in output


def test_render_svg_moves_client_label_into_node():
    output = svg_module.render_svg(
        [Edge("Switch", "Client", label="Switch: Port 5 <-> Client")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert 'class="node-port"' in output
    assert "Switch: Port 5" in output
    assert 'text-anchor="middle" fill="#555">Port 5' not in output


def test_render_svg_wraps_client_label():
    output = svg_module.render_svg(
        [Edge("Switch", "Client", label="Switch: Port 5 (very long uplink name)")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "<tspan" in output


def test_extract_port_text_non_port_prefix():
    assert svg_module._extract_port_text("eth0") is None


def test_wrap_text_splits_without_space():
    assert svg_module._wrap_text("ABCDEFGHI", max_len=4) == ["ABCD", "EFGHI"]


def test_label_metrics_empty_lines():
    assert svg_module._label_metrics([], font_size=10, padding_x=4, padding_y=3) == (8.0, 6.0)


def test_compact_edge_label_swaps_when_nodes_reversed():
    label = "B: Port 1 <-> A: Port 2"
    assert (
        svg_module._compact_edge_label(label, left_node="A", right_node="B")
        == "A Port 2 <-> Port 1"
    )


def test_render_svg_prefixes_upstream_for_port_only_label():
    output = svg_module.render_svg(
        [Edge("Switch A", "Switch B", label="Port 1 <-> Port 2")],
        node_types={"Switch A": "switch", "Switch B": "switch"},
    )
    assert "Switch A Port 1" in output


def test_render_svg_isometric_renders_label_tile():
    output = svg_module.render_svg_isometric(
        [Edge("A", "B", label="A: Port 1 <-> B: Port 2")],
        node_types={"A": "switch", "B": "switch"},
    )
    assert 'class="label-tile"' in output


def test_load_icons_missing_files_returns_empty(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _self: False)
    assert svg_module._load_icons() == {}


def test_load_isometric_icons_missing_files_returns_empty(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _self: False)
    assert svg_module._load_isometric_icons() == {}


def test_tree_layout_indices_cycle_returns_nodes():
    positions, _levels = svg_module._tree_layout_indices(
        [Edge("A", "B"), Edge("B", "A")],
        {"A": "switch", "B": "switch"},
    )
    assert set(positions.keys()) == {"A", "B"}


def test_tree_layout_indices_empty_returns_empty():
    positions, _levels = svg_module._tree_layout_indices([], {})
    assert positions == {}


def test_render_svg_isometric_handles_no_edges():
    output = svg_module.render_svg_isometric([], node_types={})
    assert output.startswith("<svg")


def test_render_svg_client_label_without_arrow():
    output = svg_module.render_svg(
        [Edge("Switch", "Client", label="Switch: Port 3")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 3" in output


def test_compact_edge_label_right_port_only():
    assert svg_module._compact_edge_label("Switch <-> Port 2") == "Port 2"


def test_compact_edge_label_left_port_only():
    assert svg_module._compact_edge_label("Port 1 <-> Switch") == "Port 1"


def test_compact_edge_label_no_ports_returns_label():
    assert svg_module._compact_edge_label("A <-> B") == "A <-> B"


def test_render_svg_client_label_left_side():
    output = svg_module.render_svg(
        [Edge("Client", "Switch", label="Switch: Port 4")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 4" in output


def test_render_svg_isometric_client_label_without_arrow():
    output = svg_module.render_svg_isometric(
        [Edge("Switch", "Client", label="Switch: Port 4")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 4" in output


def test_render_svg_handles_missing_positions(monkeypatch):
    monkeypatch.setattr(svg_module, "_layout_nodes", lambda _e, _n, _o: ({}, 0, 0))
    output = svg_module.render_svg([Edge("A", "B")], node_types={"A": "switch", "B": "switch"})
    assert "<path" not in output


def test_render_svg_without_icons(monkeypatch):
    monkeypatch.setattr(svg_module, "_load_icons", lambda: {})
    output = svg_module.render_svg([Edge("A", "B")], node_types={"A": "switch", "B": "switch"})
    assert "<image" not in output


def test_render_svg_isometric_without_icons(monkeypatch):
    monkeypatch.setattr(svg_module, "_load_isometric_icons", lambda: {})
    output = svg_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert "<image" not in output


def test_render_svg_isometric_skips_missing_positions(monkeypatch):
    monkeypatch.setattr(svg_module, "_tree_layout_indices", lambda _e, _n: ({}, {}))
    output = svg_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert "<path" not in output


def test_render_svg_isometric_elbow_path():
    output = svg_module.render_svg_isometric(
        [Edge("Root", "B"), Edge("Root", "C")],
        node_types={"Root": "gateway", "B": "switch", "C": "switch"},
    )
    assert output.count(" L ") >= 2


def test_render_svg_isometric_poe_icon():
    output = svg_module.render_svg_isometric(
        [Edge("A", "B", poe=True)],
        node_types={"A": "switch", "B": "switch"},
    )
    assert "⚡" in output


def test_render_svg_isometric_client_left_label():
    output = svg_module.render_svg_isometric(
        [Edge("Client", "Switch", label="Switch: Port 2")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 2" in output


def test_render_svg_isometric_port_prefixes_upstream():
    output = svg_module.render_svg_isometric(
        [Edge("Switch", "AP", label="Port 1 <-> Port 2")],
        node_types={"Switch": "switch", "AP": "ap"},
    )
    assert "Switch: Port 1" in output


def test_render_svg_isometric_defs_use_iso_node_prefix():
    output = svg_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert 'id="iso-node-switch"' in output


def test_render_svg_isometric_nodes_reference_iso_node_prefix():
    output = svg_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert 'fill="url(#iso-node-switch)"' in output


def test_render_svg_adds_edge_data_attributes():
    output = svg_module.render_svg(
        [Edge("Gateway", "Switch")],
        node_types={"Gateway": "gateway", "Switch": "switch"},
    )
    assert 'data-edge-left="Gateway"' in output
    assert 'data-edge-right="Switch"' in output


def test_render_svg_escapes_edge_data_attributes():
    output = svg_module.render_svg(
        [Edge('Node "A"', "Node <B>")],
        node_types={'Node "A"': "gateway", "Node <B>": "switch"},
    )
    assert 'data-edge-left="Node &quot;A&quot;"' in output
    assert 'data-edge-right="Node &lt;B&gt;"' in output


def test_render_svg_isometric_adds_edge_data_attributes():
    output = svg_module.render_svg_isometric(
        [Edge("Gateway", "Switch")],
        node_types={"Gateway": "gateway", "Switch": "switch"},
    )
    assert 'data-edge-left="Gateway"' in output
    assert 'data-edge-right="Switch"' in output
