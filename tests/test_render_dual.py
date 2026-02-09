"""Tests for dual SVG rendering (physical + VLAN)."""

from unifi_network_maps.model.topology import Edge
from unifi_network_maps.render.svg import SvgOptions, render_dual


def _basic_edges() -> list[Edge]:
    return [
        Edge("GW", "SW", vlans=(1, 10), active_vlans=(1, 10)),
        Edge("SW", "AP", vlans=(10,), active_vlans=(10,)),
    ]


def _basic_node_types() -> dict[str, str]:
    return {"GW": "gateway", "SW": "switch", "AP": "ap"}


def test_render_dual_returns_both_keys():
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
        vlan_names={1: "LAN", 10: "IoT"},
    )
    assert "physical" in result
    assert "vlan" in result
    assert result["physical"] is not None
    assert result["vlan"] is not None


def test_render_dual_physical_is_valid_svg():
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
        vlan_names={1: "LAN", 10: "IoT"},
    )
    physical = result["physical"]
    assert physical is not None
    assert physical.startswith("<svg")
    assert physical.strip().endswith("</svg>")


def test_render_dual_vlan_contains_group_boundaries():
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
        vlan_names={1: "LAN", 10: "IoT"},
    )
    vlan_svg = result["vlan"]
    assert vlan_svg is not None
    assert 'class="group-boundary"' in vlan_svg
    assert "LAN" in vlan_svg or "IoT" in vlan_svg


def test_render_dual_physical_has_no_groups():
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
        vlan_names={1: "LAN", 10: "IoT"},
    )
    physical = result["physical"]
    assert physical is not None
    assert 'class="group-boundary"' not in physical


def test_render_dual_no_vlan_data_returns_none():
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
    )
    assert result["physical"] is not None
    assert result["vlan"] is None


def test_render_dual_empty_vlan_names_returns_none():
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
        vlan_names={},
    )
    assert result["vlan"] is None


def test_render_dual_vlan_node_map_override():
    edges = [Edge("A", "B"), Edge("B", "C")]
    node_types = {"A": "gateway", "B": "switch", "C": "ap"}
    result = render_dual(
        edges,
        node_types=node_types,
        vlan_node_map={"A": 1, "B": 1, "C": 20},
        vlan_names={1: "Management", 20: "Guest"},
    )
    vlan_svg = result["vlan"]
    assert vlan_svg is not None
    assert "Management" in vlan_svg
    assert "Guest" in vlan_svg


def test_render_dual_vlan_node_map_unassigned():
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    result = render_dual(
        edges,
        node_types=node_types,
        vlan_node_map={"A": 1, "B": None},
        vlan_names={1: "LAN"},
    )
    vlan_svg = result["vlan"]
    assert vlan_svg is not None
    assert "Unassigned" in vlan_svg


def test_render_dual_isometric():
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
        vlan_names={1: "LAN", 10: "IoT"},
        isometric=True,
    )
    physical = result["physical"]
    vlan_svg = result["vlan"]
    assert physical is not None
    assert vlan_svg is not None
    # Isometric SVGs use "iso-" prefix in defs
    assert "iso-node-gateway" in physical
    assert "iso-node-gateway" in vlan_svg


def test_render_dual_both_contain_same_nodes():
    edges = _basic_edges()
    node_types = _basic_node_types()
    result = render_dual(
        edges,
        node_types=node_types,
        vlan_names={1: "LAN", 10: "IoT"},
    )
    physical = result["physical"]
    vlan_svg = result["vlan"]
    assert physical is not None
    assert vlan_svg is not None
    for node_name in node_types:
        assert node_name in physical
        assert node_name in vlan_svg


def test_render_dual_options_preserved():
    """Width/height overrides are applied to both SVGs."""
    result = render_dual(
        _basic_edges(),
        node_types=_basic_node_types(),
        options=SvgOptions(width=800, height=600),
        vlan_names={1: "LAN", 10: "IoT"},
    )
    physical = result["physical"]
    vlan_svg = result["vlan"]
    assert physical is not None
    assert vlan_svg is not None
    assert 'width="800"' in physical
    assert 'width="800"' in vlan_svg


def test_render_dual_vlan_node_map_without_names():
    """vlan_node_map works even without vlan_names (uses VLAN ID fallback)."""
    edges = [Edge("A", "B")]
    node_types = {"A": "gateway", "B": "switch"}
    result = render_dual(
        edges,
        node_types=node_types,
        vlan_node_map={"A": 5, "B": 5},
    )
    vlan_svg = result["vlan"]
    assert vlan_svg is not None
    assert "VLAN 5" in vlan_svg
