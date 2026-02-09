import re
from pathlib import Path

import unifi_network_maps.render.svg as svg_module
import unifi_network_maps.render.svg_icons as svg_icons_module
import unifi_network_maps.render.svg_isometric as svg_iso_module
import unifi_network_maps.render.svg_labels as svg_labels_module
import unifi_network_maps.render.svg_layout as svg_layout_module
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
    assert "poe-bolt" in output


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
    assert svg_labels_module._extract_port_text("eth0") is None


def test_wrap_text_splits_without_space():
    assert svg_labels_module._wrap_text("ABCDEFGHI", max_len=4) == ["ABCD", "EFGHI"]


def test_label_metrics_empty_lines():
    assert svg_labels_module._label_metrics([], font_size=10, padding_x=4, padding_y=3) == (
        8.0,
        6.0,
    )


def test_compact_edge_label_swaps_when_nodes_reversed():
    label = "B: Port 1 <-> A: Port 2"
    assert (
        svg_labels_module._compact_edge_label(label, left_node="A", right_node="B")
        == "A Port 2 <-> Port 1"
    )


def test_render_svg_prefixes_upstream_for_port_only_label():
    output = svg_module.render_svg(
        [Edge("Switch A", "Switch B", label="Port 1 <-> Port 2")],
        node_types={"Switch A": "switch", "Switch B": "switch"},
    )
    assert "Switch A Port 1" in output


def test_render_svg_isometric_renders_label_tile():
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B", label="A: Port 1 <-> B: Port 2")],
        node_types={"A": "switch", "B": "switch"},
    )
    assert 'class="label-tile"' in output


def test_load_icons_missing_files_returns_empty(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _self: False)
    assert svg_module._load_icons() == {}


def test_load_isometric_icons_missing_files_returns_empty(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda _self: False)
    assert svg_icons_module._load_isometric_icons() == {}


def test_tree_layout_indices_cycle_returns_nodes():
    positions, _levels = svg_layout_module._tree_layout_indices(
        [Edge("A", "B"), Edge("B", "A")],
        {"A": "switch", "B": "switch"},
    )
    assert set(positions.keys()) == {"A", "B"}


def test_tree_layout_indices_empty_returns_empty():
    positions, _levels = svg_layout_module._tree_layout_indices([], {})
    assert positions == {}


def test_render_svg_isometric_handles_no_edges():
    output = svg_iso_module.render_svg_isometric([], node_types={})
    assert output.startswith("<svg")


def test_render_svg_client_label_without_arrow():
    output = svg_module.render_svg(
        [Edge("Switch", "Client", label="Switch: Port 3")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 3" in output


def test_compact_edge_label_right_port_only():
    assert svg_labels_module._compact_edge_label("Switch <-> Port 2") == "Port 2"


def test_compact_edge_label_left_port_only():
    assert svg_labels_module._compact_edge_label("Port 1 <-> Switch") == "Port 1"


def test_compact_edge_label_no_ports_returns_label():
    assert svg_labels_module._compact_edge_label("A <-> B") == "A <-> B"


def test_render_svg_client_label_left_side():
    output = svg_module.render_svg(
        [Edge("Client", "Switch", label="Switch: Port 4")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 4" in output


def test_render_svg_isometric_client_label_without_arrow():
    output = svg_iso_module.render_svg_isometric(
        [Edge("Switch", "Client", label="Switch: Port 4")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 4" in output


def test_render_svg_handles_missing_positions(monkeypatch):
    monkeypatch.setattr(svg_module, "_layout_nodes", lambda _e, _n, _o: ({}, 0, 0))
    output = svg_module.render_svg([Edge("A", "B")], node_types={"A": "switch", "B": "switch"})
    # No edge paths should be rendered (path with stroke attribute)
    assert 'stroke="url(#link' not in output


def test_render_svg_without_icons(monkeypatch):
    monkeypatch.setattr(
        svg_module, "_load_icons", lambda icon_set="isometric", decal_color="#1a1a1a": {}
    )
    output = svg_module.render_svg([Edge("A", "B")], node_types={"A": "switch", "B": "switch"})
    assert "<image" not in output


def test_render_svg_isometric_without_icons(monkeypatch):
    monkeypatch.setattr(
        svg_iso_module,
        "_load_isometric_icons",
        lambda icon_set="isometric", decal_color="#5A6878", decal_colors=None: {},
    )
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert "<image" not in output


def test_render_svg_isometric_skips_missing_positions(monkeypatch):
    monkeypatch.setattr(svg_layout_module, "_tree_layout_indices", lambda _e, _n: ({}, {}))
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    # No edge paths should be rendered (path with stroke attribute)
    assert 'stroke="url(#iso-link' not in output


def test_render_svg_isometric_elbow_path():
    output = svg_iso_module.render_svg_isometric(
        [Edge("Root", "B"), Edge("Root", "C")],
        node_types={"Root": "gateway", "B": "switch", "C": "switch"},
    )
    assert output.count(" L ") >= 2


def test_render_svg_isometric_poe_icon():
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B", poe=True)],
        node_types={"A": "switch", "B": "switch"},
    )
    assert "iso-poe-bolt" in output


def test_render_svg_isometric_client_left_label():
    output = svg_iso_module.render_svg_isometric(
        [Edge("Client", "Switch", label="Switch: Port 2")],
        node_types={"Switch": "switch", "Client": "client"},
    )
    assert "Switch: Port 2" in output


def test_render_svg_isometric_port_prefixes_upstream():
    output = svg_iso_module.render_svg_isometric(
        [Edge("Switch", "AP", label="Port 1 <-> Port 2")],
        node_types={"Switch": "switch", "AP": "ap"},
    )
    assert "Switch: Port 1" in output


def test_render_svg_isometric_defs_use_iso_node_prefix():
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")], node_types={"A": "switch", "B": "switch"}
    )
    assert 'id="iso-node-switch"' in output


def test_render_svg_isometric_nodes_reference_iso_node_prefix():
    output = svg_iso_module.render_svg_isometric(
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
    output = svg_iso_module.render_svg_isometric(
        [Edge("Gateway", "Switch")],
        node_types={"Gateway": "gateway", "Switch": "switch"},
    )
    assert 'data-edge-left="Gateway"' in output
    assert 'data-edge-right="Switch"' in output


# Icon set tests


def test_load_isometric_icons_isometric():
    icons = svg_icons_module._load_isometric_icons("isometric")
    assert "gateway" in icons
    assert "switch" in icons
    assert "ap" in icons
    assert "client" in icons
    assert "other" in icons
    assert all(v.startswith("data:image/svg+xml;base64,") for v in icons.values())


def test_load_isometric_icons_modern():
    icons = svg_icons_module._load_isometric_icons("modern")
    assert "gateway" in icons
    assert "switch" in icons
    assert "ap" in icons
    assert "client" in icons
    assert "other" in icons
    assert all(v.startswith("data:image/svg+xml;base64,") for v in icons.values())


def test_load_isometric_icons_fallback_to_isometric():
    """Unknown icon set should fall back to isometric."""
    icons = svg_icons_module._load_isometric_icons("nonexistent_set")
    assert "gateway" in icons
    assert len(icons) > 0


def test_load_icons_isometric():
    icons = svg_module._load_icons("isometric")
    assert "gateway" in icons
    assert "switch" in icons


def test_load_icons_modern():
    icons = svg_module._load_icons("modern")
    assert "gateway" in icons
    assert "switch" in icons


def test_darken_hex_basic():
    assert svg_icons_module._darken_hex("#ffffff", 0.5) == "#7f7f7f"
    assert svg_icons_module._darken_hex("#000000", 0.5) == "#000000"


def test_darken_hex_typical_factor():
    result = svg_icons_module._darken_hex("#006fff", 0.35)
    assert result == "#0048a5"


def test_darken_hex_zero_factor():
    assert svg_icons_module._darken_hex("#ff8000", 0.0) == "#ff8000"


def test_darken_hex_invalid_input():
    assert svg_icons_module._darken_hex("not-a-color", 0.35) == "not-a-color"
    assert svg_icons_module._darken_hex("#fff", 0.35) == "#fff"


def test_build_decal_colors_returns_all_node_types():
    from unifi_network_maps.render.svg_theme import DEFAULT_THEME

    colors = svg_icons_module._build_decal_colors(DEFAULT_THEME)
    expected = {
        "gateway",
        "switch",
        "ap",
        "client",
        "other",
        "client_cluster",
        "camera",
        "tv",
        "phone",
        "printer",
        "nas",
        "speaker",
        "game_console",
        "iot",
    }
    assert set(colors.keys()) == expected
    for color in colors.values():
        assert color.startswith("#")
        assert len(color) == 7


def test_build_decal_colors_are_darker_than_source():
    from unifi_network_maps.render.svg_theme import DEFAULT_THEME

    colors = svg_icons_module._build_decal_colors(DEFAULT_THEME)
    # Gateway source "to" is #ffb15a, decal should be darker (lower RGB sum)
    source = DEFAULT_THEME.node_gateway[1]
    decal = colors["gateway"]
    src_sum = sum(int(source[i : i + 2], 16) for i in (1, 3, 5))
    dec_sum = sum(int(decal[i : i + 2], 16) for i in (1, 3, 5))
    assert dec_sum < src_sum


def test_build_font_style_none():
    face, family = svg_module._build_font_style(None)
    assert face == ""
    assert family == "Arial,Helvetica,sans-serif"


def test_build_font_style_unknown_font():
    face, family = svg_module._build_font_style("Nonexistent Font")
    assert face == ""
    assert family == "Arial,Helvetica,sans-serif"


def test_build_font_style_inter():
    face, family = svg_module._build_font_style("Inter")
    assert "@font-face" in face
    assert "font-weight:400" in face
    assert "font-weight:600" in face
    assert "'Inter'" in family


def test_build_font_style_space_grotesk():
    face, family = svg_module._build_font_style("Space Grotesk")
    assert "@font-face" in face
    assert "'Space Grotesk'" in family


def test_svg_style_block_no_font():
    from unifi_network_maps.render.svg_theme import DEFAULT_THEME

    block = svg_module._svg_style_block(DEFAULT_THEME, 12)
    assert "<style>" in block
    assert "font-weight:600" in block
    assert "@font-face" not in block


def test_svg_style_block_with_font():
    from dataclasses import replace

    from unifi_network_maps.render.svg_theme import DEFAULT_THEME

    theme = replace(DEFAULT_THEME, font_family="Inter")
    block = svg_module._svg_style_block(theme, 12)
    assert "@font-face" in block
    assert "'Inter'" in block
    assert "node-label" in block


def test_svg_style_block_iso_mode():
    from unifi_network_maps.render.svg_theme import DEFAULT_THEME

    block = svg_module._svg_style_block(DEFAULT_THEME, 12, iso=True)
    assert "not(.group-label)" in block


def test_render_svg_uses_theme_icon_set():
    """SVG render should use icon_set from theme."""
    from dataclasses import replace

    from unifi_network_maps.render.svg_theme import DEFAULT_THEME

    theme = replace(DEFAULT_THEME, icon_set="modern")
    output = svg_module.render_svg(
        [Edge("A", "B")],
        node_types={"A": "gateway", "B": "switch"},
        theme=theme,
    )
    assert "<svg" in output


def test_render_svg_isometric_uses_theme_icon_set():
    """Isometric SVG render should use icon_set from theme."""
    from dataclasses import replace

    from unifi_network_maps.render.svg_theme import DEFAULT_THEME

    theme = replace(DEFAULT_THEME, icon_set="modern")
    output = svg_iso_module.render_svg_isometric(
        [Edge("A", "B")],
        node_types={"A": "gateway", "B": "switch"},
        theme=theme,
    )
    assert "<svg" in output
