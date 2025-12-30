from unifi_mermaid.mermaid import render_mermaid
from unifi_mermaid.topology import Edge


def test_render_mermaid_uses_ids_with_labels():
    output = render_mermaid([Edge("AP Wifi6 tuinhuis", "Core Switch")])
    assert 'ap_wifi6_tuinhuis["AP Wifi6 tuinhuis"]' in output


def test_render_mermaid_includes_edge_label():
    output = render_mermaid([Edge("A", "B", label="Port 1")])
    assert '---|"Port 1"|' in output


def test_render_mermaid_styles_poe_links():
    output = render_mermaid([Edge("A", "B", poe=True)])
    assert "linkStyle 0" in output


def test_render_mermaid_includes_legend():
    output = render_mermaid([Edge("A", "B")], include_legend=True)
    assert "subgraph legend" in output
