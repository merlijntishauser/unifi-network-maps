from unifi_mermaid.mermaid import render_legend, render_mermaid
from unifi_mermaid.topology import Edge


def test_render_mermaid_uses_ids_with_labels():
    output = render_mermaid([Edge("AP Wifi6 tuinhuis", "Core Switch")])
    assert 'ap_wifi6_tuinhuis["AP Wifi6 tuinhuis"]' in output


def test_render_mermaid_includes_edge_label():
    output = render_mermaid([Edge("A", "B", label="Port 1")])
    assert '---|"Port 1"|' in output


def test_render_mermaid_styles_poe_links():
    output = render_mermaid([Edge("A", "B", poe=True)])
    assert "linkStyle 0 stroke:#1e88e5" in output


def test_render_legend_outputs_subgraph():
    output = render_legend()
    assert "subgraph legend" in output


def test_render_mermaid_renders_group_subgraph():
    output = render_mermaid([Edge("Gateway", "Switch")], groups={"gateway": ["Gateway"]})
    assert "subgraph group_gateway" in output


def test_render_mermaid_assigns_class_for_node_types():
    output = render_mermaid([Edge("A", "B")], node_types={"A": "gateway"})
    assert "class a node_gateway" in output


def test_render_mermaid_escapes_quotes():
    output = render_mermaid([Edge('A "1"', "B")])
    assert '\\"' in output
