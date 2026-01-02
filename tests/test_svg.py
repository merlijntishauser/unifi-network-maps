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
