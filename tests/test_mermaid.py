from unifi_network_maps.model.topology import Edge
from unifi_network_maps.render.mermaid import render_legend, render_legend_compact, render_mermaid


def test_render_mermaid_uses_ids_with_labels():
    output = render_mermaid([Edge("AP Wifi6 tuinhuis", "Core Switch")])
    assert 'ap_wifi6_tuinhuis["AP Wifi6 tuinhuis"]' in output


def test_render_mermaid_includes_edge_label():
    output = render_mermaid([Edge("A", "B", label="Port 1")])
    assert '---|"Port 1"|' in output


def test_render_mermaid_styles_poe_links():
    output = render_mermaid([Edge("A", "B", poe=True)])
    assert "linkStyle 0 stroke:#1e88e5" in output


def test_render_mermaid_styles_wireless_links():
    output = render_mermaid([Edge("A", "B", wireless=True)])
    assert "stroke-dasharray: 5 4" in output


def test_render_legend_outputs_subgraph():
    output = render_legend()
    assert "subgraph legend" in output


def test_render_mermaid_grouped_uses_semicolons():
    output = render_mermaid(
        [Edge("A", "B")],
        groups={"group": ["A", "B"]},
        group_order=["group"],
        node_types={"A": "gateway", "B": "switch"},
    )
    lines = output.splitlines()
    assert '  subgraph group_group["Group"];' in lines
    assert any(line.endswith(";") for line in lines if "---" in line)
    assert any(line.endswith(";") for line in lines if line.strip().startswith("class "))


def test_render_legend_link_inside_subgraph():
    output = render_legend().splitlines()
    link_line = "    legend_poe_a ---|⚡| legend_poe_b;"
    end_line = "  end"
    assert link_line in output
    assert output.index(link_line) < output.index(end_line)
    assert "    legend_no_poe_a --- legend_no_poe_b;" in output
    assert "    linkStyle 0 arrowhead:none;" in output
    assert "    linkStyle 1 arrowhead:none;" in output


def test_render_legend_subgraph_ends_with_semicolon():
    output = render_legend().splitlines()
    assert '  subgraph legend["Legend"];' in output


def test_render_legend_link_style_default():
    output = render_legend().splitlines()
    assert "  linkStyle 0 stroke:#1e88e5,stroke-width:2px,arrowhead:none;" in output
    assert "  linkStyle 1 stroke:#2ecc71,stroke-width:2px,arrowhead:none;" in output


def test_render_legend_class_lines_end_with_semicolon():
    output = render_legend().splitlines()
    assert "  class legend_gateway node_gateway;" in output


def test_render_legend_compact_outputs_table():
    output = render_legend_compact()
    assert '<table class="unifi-legend-table">' in output
    assert "background:#ffe3b3" in output
    assert "Link</span>" in output
    assert "Link</span>" in output and "⚡" not in output.split("Link</span>")[1]


def test_render_mermaid_renders_group_subgraph():
    output = render_mermaid([Edge("Gateway", "Switch")], groups={"gateway": ["Gateway"]})
    assert "subgraph group_gateway" in output


def test_render_mermaid_assigns_class_for_node_types():
    output = render_mermaid([Edge("A", "B")], node_types={"A": "gateway"})
    assert "class a node_gateway" in output


def test_render_mermaid_escapes_quotes():
    output = render_mermaid([Edge('A "1"', "B")])
    assert '\\"' in output


def test_render_mermaid_escapes_backslashes():
    output = render_mermaid([Edge("A \\ 1", "B")])
    assert "\\\\" in output


def test_render_mermaid_escapes_newlines():
    output = render_mermaid([Edge("Line 1\nLine 2", "B")])
    assert "\\n" in output
