import re

from unifi_network_maps.model.topology import Edge
from unifi_network_maps.render.svg import render_svg_isometric


def test_render_svg_isometric_outputs_svg_root():
    output = render_svg_isometric([Edge("A", "B")], node_types={"A": "gateway", "B": "switch"})
    assert output.startswith("<svg")


def test_render_svg_isometric_includes_polygons():
    output = render_svg_isometric([Edge("A", "B")], node_types={"A": "gateway", "B": "switch"})
    assert "<path" in output


def test_render_svg_isometric_dashes_wireless_links():
    output = render_svg_isometric(
        [Edge("A", "B", wireless=True)],
        node_types={"A": "gateway", "B": "switch"},
    )
    assert 'stroke-dasharray="8 6"' in output


def _parse_points(points: str) -> list[tuple[float, float]]:
    coords = []
    for pair in points.strip().split():
        x_str, y_str = pair.split(",", 1)
        coords.append((float(x_str), float(y_str)))
    return coords


def test_isometric_label_tile_stacks_without_gap():
    output = render_svg_isometric(
        [Edge("A", "B", label="A: Port 1 <-> Port 2")],
        node_types={"A": "gateway", "B": "switch"},
    )
    polygons: list[tuple[str | None, list[tuple[float, float]]]] = []
    for match in re.finditer(r"<polygon([^>]*)>", output):
        attrs = match.group(1)
        points_match = re.search(r'points="([^"]+)"', attrs)
        if not points_match:
            continue
        cls_match = re.search(r'class="([^"]+)"', attrs)
        cls = cls_match.group(1) if cls_match else None
        polygons.append((cls, _parse_points(points_match.group(1))))

    label_index = next(i for i, (cls, _points) in enumerate(polygons) if cls == "label-tile")
    side_index = max(i for i in range(label_index) if polygons[i][0] == "label-tile-side")
    node_index = max(i for i in range(side_index) if polygons[i][0] is None)

    node_top_bottom_y = max(y for _x, y in polygons[node_index][1])
    side_bottom_y = max(y for _x, y in polygons[side_index][1])

    assert abs(side_bottom_y - node_top_bottom_y) < 0.01


def test_isometric_label_truncates_long_text():
    output = render_svg_isometric(
        [
            Edge(
                "A",
                "B",
                label="Very Long Switch Name: Port 12 <-> Port 23 Extra Extra Extra",
            )
        ],
        node_types={"A": "gateway", "B": "switch"},
    )
    tspans = re.findall(r"<tspan[^>]*>([^<]+)</tspan>", output)
    unescaped = (
        text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&") for text in tspans
    )
    max_len = max(len(text) for text in unescaped)
    max_chars = int((160 * 1.5 * 0.6) / (8 * 0.6))
    assert max_len <= max_chars
