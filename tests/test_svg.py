from unifi_mermaid.svg import SvgOptions, render_svg
from unifi_mermaid.topology import Edge


def test_render_svg_outputs_svg_root():
    output = render_svg([Edge("A", "B")], node_types={"A": "gateway", "B": "switch"})
    assert output.startswith("<svg")


def test_render_svg_respects_size_override():
    output = render_svg(
        [Edge("A", "B")],
        node_types={"A": "gateway", "B": "switch"},
        options=SvgOptions(width=800, height=600),
    )
    assert 'width="800"' in output


def test_render_svg_escapes_edge_labels():
    output = render_svg(
        [Edge("A", "B", label="Port 1 <-> Port 2")],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert "&lt;-&gt;" in output


def test_render_svg_renders_poe_icon():
    output = render_svg(
        [Edge("A", "B", poe=True)],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert "⚡" in output


def test_render_svg_compacts_device_labels():
    output = render_svg(
        [Edge("A", "B", label="Switch A: Port 2 <-> Switch B: Port 5")],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert 'class="node-port"' in output
    assert "Switch A Port 2" in output
    assert ">5</tspan>" in output


def test_render_svg_orders_upstream_label():
    output = render_svg(
        [Edge("Parent", "Child", label="Child: Port 1 <-> Parent: Port 2")],
        node_types={"Parent": "switch", "Child": "switch"},
    )
    assert "Parent Port 2 &lt;-&gt; Port 1" in output


def test_render_svg_moves_client_label_into_node():
    output = render_svg(
        [Edge("Switch", "Client", label="Switch: Port 5 <-> Client")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert 'class="node-port"' in output
    assert "Switch: Port 5" in output
    assert 'text-anchor="middle" fill="#555">Port 5' not in output


def test_render_svg_wraps_client_label():
    output = render_svg(
        [Edge("Switch", "Client", label="Switch: Port 5 (very long uplink name)")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "<tspan" in output
