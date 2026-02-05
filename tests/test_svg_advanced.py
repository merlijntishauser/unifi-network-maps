"""Tests for advanced SVG features: VLANs, WAN upstream, and node data."""

from __future__ import annotations

from unifi_network_maps.model.topology import Edge, WanInfo, WanInterface
from unifi_network_maps.render.svg import (
    SvgOptions,
    _edge_opacity,
    _render_vlan_endpoint_markers,
    _vlan_data_attrs,
    render_svg,
)
from unifi_network_maps.render.svg_isometric import (
    _render_iso_vlan_striped_edge,
    render_svg_isometric,
)
from unifi_network_maps.render.svg_theme import DEFAULT_THEME

# --- VLAN data attributes ---


class TestVlanDataAttrs:
    def test_empty_edge(self):
        edge = Edge("A", "B")
        assert _vlan_data_attrs(edge) == ""

    def test_vlans_only(self):
        edge = Edge("A", "B", vlans=(10, 20, 30))
        attrs = _vlan_data_attrs(edge)
        assert 'data-vlans="10,20,30"' in attrs

    def test_active_vlans(self):
        edge = Edge("A", "B", active_vlans=(10,))
        attrs = _vlan_data_attrs(edge)
        assert 'data-active-vlans="10"' in attrs

    def test_trunk(self):
        edge = Edge("A", "B", is_trunk=True)
        attrs = _vlan_data_attrs(edge)
        assert 'data-trunk="true"' in attrs

    def test_all_vlan_attrs(self):
        edge = Edge("A", "B", vlans=(10, 20), active_vlans=(10,), is_trunk=True)
        attrs = _vlan_data_attrs(edge)
        assert 'data-vlans="10,20"' in attrs
        assert 'data-active-vlans="10"' in attrs
        assert 'data-trunk="true"' in attrs


# --- Edge opacity ---


class TestEdgeOpacity:
    def test_infrastructure_edge(self):
        node_types = {"Switch": "switch", "AP": "ap"}
        edge = Edge("Switch", "AP")
        assert _edge_opacity(node_types, edge) == 1.0

    def test_client_edge_right(self):
        node_types = {"Switch": "switch", "Client": "client"}
        edge = Edge("Switch", "Client")
        assert _edge_opacity(node_types, edge) == 0.5

    def test_client_edge_left(self):
        node_types = {"Client": "client", "Switch": "switch"}
        edge = Edge("Client", "Switch")
        assert _edge_opacity(node_types, edge) == 0.5


# --- VLAN endpoint markers ---


class TestRenderVlanEndpointMarkers:
    def test_empty_vlans(self):
        lines = []
        _render_vlan_endpoint_markers(lines, 100, 100, (), DEFAULT_THEME)
        assert lines == []

    def test_single_vlan(self):
        lines = []
        _render_vlan_endpoint_markers(lines, 100, 100, (10,), DEFAULT_THEME)
        assert len(lines) == 1
        assert "<rect" in lines[0]
        assert 'data-vlan="10"' in lines[0]

    def test_multiple_vlans_limited(self):
        lines = []
        vlans = (10, 20, 30, 40, 50)  # More than max_markers=4
        _render_vlan_endpoint_markers(lines, 100, 100, vlans, DEFAULT_THEME, max_markers=4)
        assert len(lines) == 4  # Only first 4


# --- WAN upstream rendering (orthogonal) ---


class TestWanUpstreamRendering:
    def test_single_wan(self):
        wan = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan_info = WanInfo(wan1=wan, wan2=None)
        output = render_svg(
            [Edge("Gateway", "Switch")],
            node_types={"Gateway": "gateway", "Switch": "switch"},
            wan_info=wan_info,
        )
        assert 'class="wan-upstream"' in output
        assert "1GbE" in output or "1.2.3.4" in output

    def test_dual_wan(self):
        wan1 = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan2 = WanInterface(port_idx=9, link_speed=100, ip_address="5.6.7.8", enabled=True)
        wan_info = WanInfo(wan1=wan1, wan2=wan2)
        output = render_svg(
            [Edge("Gateway", "Switch")],
            node_types={"Gateway": "gateway", "Switch": "switch"},
            wan_info=wan_info,
        )
        assert "WAN1" in output or "1.2.3.4" in output
        assert "WAN2" in output or "5.6.7.8" in output

    def test_wan_with_label(self):
        wan = WanInterface(
            port_idx=1,
            link_speed=1000,
            ip_address="1.2.3.4",
            enabled=True,
            label="Fiber",
        )
        wan_info = WanInfo(wan1=wan, wan2=None)
        output = render_svg(
            [Edge("Gateway", "Switch")],
            node_types={"Gateway": "gateway", "Switch": "switch"},
            wan_info=wan_info,
        )
        assert "Fiber" in output

    def test_no_wan_info(self):
        output = render_svg(
            [Edge("Gateway", "Switch")],
            node_types={"Gateway": "gateway", "Switch": "switch"},
            wan_info=None,
        )
        assert 'class="wan-upstream"' not in output

    def test_wan_no_gateway(self):
        """WAN info should not render if no gateway node exists."""
        wan = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan_info = WanInfo(wan1=wan, wan2=None)
        output = render_svg(
            [Edge("Switch1", "Switch2")],
            node_types={"Switch1": "switch", "Switch2": "switch"},
            wan_info=wan_info,
        )
        # WAN section should not be rendered without a gateway
        assert 'class="wan-upstream"' not in output


# --- WAN upstream rendering (isometric) ---


class TestIsoWanUpstreamRendering:
    def test_single_wan_isometric(self):
        wan = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan_info = WanInfo(wan1=wan, wan2=None)
        output = render_svg_isometric(
            [Edge("Gateway", "Switch")],
            node_types={"Gateway": "gateway", "Switch": "switch"},
            wan_info=wan_info,
        )
        assert 'class="wan-upstream"' in output

    def test_wan_with_disabled_wan2(self):
        wan1 = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan2 = WanInterface(port_idx=9, link_speed=None, ip_address=None, enabled=False)
        wan_info = WanInfo(wan1=wan1, wan2=wan2)
        output = render_svg_isometric(
            [Edge("Gateway", "Switch")],
            node_types={"Gateway": "gateway", "Switch": "switch"},
            wan_info=wan_info,
        )
        assert "disabled" in output.lower() or "WAN2" in output


# --- VLAN striped edge rendering ---


class TestVlanStripedEdgeRendering:
    def test_edge_with_active_vlans(self):
        edges = [Edge("A", "B", vlans=(10, 20), active_vlans=(10,))]
        output = render_svg(
            edges,
            node_types={"A": "gateway", "B": "switch"},
        )
        # VLAN edges should have data attributes
        assert 'data-vlans="10,20"' in output or 'data-active-vlans="10"' in output

    def test_edge_with_multiple_active_vlans(self):
        edges = [Edge("A", "B", active_vlans=(10, 20, 30))]
        output = render_svg(
            edges,
            node_types={"A": "gateway", "B": "switch"},
        )
        # Should render VLAN visualization
        assert "<path" in output


# --- ISO VLAN striped edge ---


class TestIsoVlanStripedEdge:
    def test_empty_vlans(self):
        lines = []
        _render_iso_vlan_striped_edge(
            lines, "M 0 0 L 100 100", (), DEFAULT_THEME, 4, False, "", 1.0
        )
        assert lines == []

    def test_single_vlan(self):
        lines = []
        _render_iso_vlan_striped_edge(
            lines, "M 0 0 L 100 100", (10,), DEFAULT_THEME, 4, False, "", 1.0
        )
        # Should have glow + 1 color layer
        assert len(lines) >= 2

    def test_wireless_dash_pattern(self):
        lines = []
        _render_iso_vlan_striped_edge(
            lines, "M 0 0 L 100 100", (10,), DEFAULT_THEME, 4, True, "", 1.0
        )
        assert any("stroke-dasharray" in line for line in lines)

    def test_reduced_opacity(self):
        lines = []
        _render_iso_vlan_striped_edge(
            lines, "M 0 0 L 100 100", (10,), DEFAULT_THEME, 4, False, "", 0.5
        )
        assert any('opacity="0.5"' in line for line in lines)


# --- Node data attributes ---


class TestNodeDataAttributes:
    def test_node_data_adds_attributes(self):
        output = render_svg(
            [Edge("A", "B")],
            node_types={"A": "gateway", "B": "switch"},
            node_data={"A": {"data-custom": "value"}},
        )
        assert 'data-custom="value"' in output

    def test_node_data_merges_class(self):
        output = render_svg(
            [Edge("A", "B")],
            node_types={"A": "gateway", "B": "switch"},
            node_data={"A": {"class": "highlighted"}},
        )
        assert 'class="unm-node highlighted"' in output


# --- Isometric group bounds ---


class TestIsoGroupBounds:
    def test_single_node_group(self):
        """Single-node groups should get centered boundaries."""
        edges = [Edge("Gateway", "Switch")]
        node_types = {"Gateway": "gateway", "Switch": "switch"}
        groups = {"Core": ["Gateway"]}
        output = render_svg_isometric(
            edges,
            node_types=node_types,
            options=SvgOptions(layout_mode="grouped"),
            groups=groups,
        )
        assert 'class="group-boundary"' in output

    def test_empty_group_skipped(self):
        """Groups with no matching nodes should be skipped."""
        edges = [Edge("A", "B")]
        node_types = {"A": "gateway", "B": "switch"}
        groups = {"Empty": ["NonExistent"]}
        output = render_svg_isometric(
            edges,
            node_types=node_types,
            options=SvgOptions(layout_mode="grouped"),
            groups=groups,
        )
        # Should still render but without the empty group
        assert output.startswith("<svg")


# --- Isometric edge PoE icon positioning ---


class TestIsoPoEPositioning:
    def test_poe_elbow_path(self):
        """PoE icon should be positioned on elbow path."""
        edges = [Edge("Root", "B", poe=True), Edge("Root", "C")]
        node_types = {"Root": "gateway", "B": "switch", "C": "switch"}
        output = render_svg_isometric(edges, node_types=node_types)
        assert "iso-poe-bolt" in output

    def test_poe_straight_path(self):
        """PoE icon on straight vertical path."""
        edges = [Edge("A", "B", poe=True)]
        node_types = {"A": "gateway", "B": "switch"}
        output = render_svg_isometric(edges, node_types=node_types)
        assert "iso-poe-bolt" in output
