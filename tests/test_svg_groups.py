"""Tests for SVG group rendering."""

import unifi_network_maps.render.svg as svg_module
from unifi_network_maps.model.topology import Edge


def test_render_svg_groups_creates_boundaries():
    """Verify group boundaries are rendered with rect elements."""
    edges = [Edge("A", "B"), Edge("A", "C")]
    node_types = {"A": "gateway", "B": "switch", "C": "ap"}
    groups = {"Core": ["A", "B"], "Wireless": ["C"]}
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups=groups,
    )
    assert 'class="group-boundary"' in output
    assert 'class="network-group"' in output


def test_render_svg_groups_renders_labels():
    """Verify group labels are rendered."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    groups = {"Infrastructure": ["A", "B"]}
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups=groups,
    )
    assert 'class="group-label"' in output
    assert "Infrastructure" in output


def test_render_svg_groups_respects_order():
    """Verify groups are rendered in specified order."""
    edges = [Edge("A", "B"), Edge("C", "D")]
    node_types = {"A": "gateway", "B": "switch", "C": "ap", "D": "client"}
    groups = {"Second": ["C", "D"], "First": ["A", "B"]}
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups=groups,
        group_order=["First", "Second"],
    )
    first_idx = output.find('data-group-name="First"')
    second_idx = output.find('data-group-name="Second"')
    assert first_idx < second_idx


def test_render_svg_groups_adds_data_group_attribute():
    """Verify nodes have data-group attribute when groups are specified."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    groups = {"Core": ["A", "B"]}
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups=groups,
    )
    assert 'data-group="Core"' in output


def test_render_svg_physical_ignores_groups():
    """Verify physical layout mode ignores groups parameter."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    groups = {"Core": ["A", "B"]}
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="physical"),
        groups=groups,
    )
    assert 'class="group-boundary"' not in output


def test_render_svg_groups_handles_empty_groups():
    """Verify empty groups dict works without error."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups={},
    )
    assert output.startswith("<svg")


def test_render_svg_groups_handles_ungrouped_nodes():
    """Verify nodes not in any group are handled."""
    edges = [Edge("A", "B"), Edge("A", "C")]
    node_types = {"A": "gateway", "B": "switch", "C": "ap"}
    groups = {"Core": ["A"]}  # B and C are not grouped
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups=groups,
    )
    assert output.startswith("<svg")
    # Ungrouped nodes should still be rendered
    assert "B" in output
    assert "C" in output


def test_render_svg_isometric_groups():
    """Verify isometric layout supports groups with parallelogram boundaries."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    groups = {"Core": ["A", "B"]}
    output = svg_module.render_svg_isometric(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups=groups,
    )
    assert 'class="group-boundary"' in output
    # Isometric uses polygon instead of rect for perspective
    assert '<polygon class="group-boundary"' in output


def test_render_svg_isometric_physical_ignores_groups():
    """Verify isometric physical mode ignores groups."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    groups = {"Core": ["A", "B"]}
    output = svg_module.render_svg_isometric(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="physical"),
        groups=groups,
    )
    assert 'class="group-boundary"' not in output


def test_render_svg_groups_none_works():
    """Verify groups=None works in grouped mode."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    output = svg_module.render_svg(
        edges,
        node_types=node_types,
        options=svg_module.SvgOptions(layout_mode="grouped"),
        groups=None,
    )
    assert output.startswith("<svg")
    assert 'class="group-boundary"' not in output


def test_assign_nodes_to_groups():
    """Test _assign_nodes_to_groups helper."""
    nodes = {"A", "B", "C"}
    groups = {"G1": ["A", "B"], "G2": ["C"]}
    result = svg_module._assign_nodes_to_groups(nodes, groups)
    assert result == {"A": "G1", "B": "G1", "C": "G2"}


def test_resolve_group_order_with_order():
    """Test _resolve_group_order with explicit order."""
    groups = {"B": ["x"], "A": ["y"], "C": ["z"]}
    result = svg_module._resolve_group_order(groups, ["A", "B", "C"])
    assert result == ["A", "B", "C"]


def test_resolve_group_order_without_order():
    """Test _resolve_group_order without explicit order."""
    groups = {"B": ["x"], "A": ["y"]}
    result = svg_module._resolve_group_order(groups, None)
    assert result == ["A", "B"]


def test_filter_edges_for_group():
    """Test _filter_edges_for_group helper."""
    edges = [Edge("A", "B"), Edge("A", "C"), Edge("C", "D")]
    group_nodes = {"A", "B"}
    result = svg_module._filter_edges_for_group(edges, group_nodes)
    assert len(result) == 1
    assert result[0].left == "A" and result[0].right == "B"


def test_build_node_to_group_map():
    """Test _build_node_to_group_map helper."""
    groups = {"G1": ["A", "B"], "G2": ["C"]}
    result = svg_module._build_node_to_group_map(groups)
    assert result == {"A": "G1", "B": "G1", "C": "G2"}
