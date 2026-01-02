from unifi_mermaid.svg import render_svg_isometric
from unifi_mermaid.topology import Edge


def test_render_svg_isometric_outputs_svg_root():
    output = render_svg_isometric([Edge("A", "B")], node_types={"A": "gateway", "B": "switch"})
    assert output.startswith("<svg")


def test_render_svg_isometric_includes_polygons():
    output = render_svg_isometric([Edge("A", "B")], node_types={"A": "gateway", "B": "switch"})
    assert "<path" in output
