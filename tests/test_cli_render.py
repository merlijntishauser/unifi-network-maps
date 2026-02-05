"""Tests for CLI render orchestration."""

from __future__ import annotations

import argparse

from unifi_network_maps.model.topology import Device, Edge, TopologyResult, UplinkInfo
from unifi_network_maps.render.mermaid_theme import DEFAULT_THEME as DEFAULT_MERMAID_THEME
from unifi_network_maps.render.svg_theme import DEFAULT_THEME as DEFAULT_SVG_THEME


def _make_minimal_device(
    name: str,
    mac: str,
    device_type: str = "switch",
) -> Device:
    return Device(
        name=name,
        model_name="Test",
        model="TEST",
        mac=mac,
        ip="192.168.1.1",
        type=device_type,
        lldp_info=[],
        port_table=[],
        poe_ports={},
        uplink=UplinkInfo(mac="00:00:00:00:00:01", name="Gateway", port=1),
        last_uplink=None,
        version="1.0",
    )


def _make_args(**kwargs) -> argparse.Namespace:
    defaults = {
        "no_cache": True,
        "debug_dump": False,
        "debug_sample": 0,
        "include_ports": False,
        "only_unifi": False,
        "include_clients": False,
        "client_scope": "all",
        "format": "mermaid",
        "direction": "TB",
        "group_by_type": False,
        "markdown": False,
        "output": None,
        "stdout": True,
        "svg_width": None,
        "svg_height": None,
        "svg_layout_mode": "physical",
        "collapse_clients": False,
        "wan_label": None,
        "wan_speed": None,
        "wan2_label": None,
        "wan2_speed": None,
        "legend_style": "auto",
        "legend_scale": 1.0,
        "mkdocs_sidebar_legend": False,
        "mkdocs_dual_theme": False,
        "mkdocs_timestamp_zone": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- render_mermaid_output ---


class TestRenderMermaidOutput:
    def test_basic_render(self):
        from unifi_network_maps.cli.render import render_mermaid_output

        args = _make_args()
        devices = [
            _make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway"),
            _make_minimal_device("Switch", "aa:bb:cc:dd:ee:02", "switch"),
        ]
        topology = TopologyResult(
            tree_edges=[Edge("Gateway", "Switch")],
            raw_edges=[],
        )

        result = render_mermaid_output(
            args,
            devices,
            topology,
            config=None,
            site="default",
            mermaid_theme=DEFAULT_MERMAID_THEME,
        )
        assert "Gateway" in result
        assert "Switch" in result

    def test_markdown_wrapping(self):
        from unifi_network_maps.cli.render import render_mermaid_output

        args = _make_args(markdown=True)
        devices = [_make_minimal_device("A", "aa:bb:cc:dd:ee:01", "gateway")]
        topology = TopologyResult(tree_edges=[], raw_edges=[])

        result = render_mermaid_output(
            args, devices, topology, None, "default", DEFAULT_MERMAID_THEME
        )
        assert "```mermaid" in result

    def test_group_by_type(self):
        from unifi_network_maps.cli.render import render_mermaid_output

        args = _make_args(group_by_type=True)
        devices = [
            _make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway"),
            _make_minimal_device("Switch", "aa:bb:cc:dd:ee:02", "switch"),
        ]
        topology = TopologyResult(
            tree_edges=[Edge("Gateway", "Switch")],
            raw_edges=[],
        )

        result = render_mermaid_output(
            args, devices, topology, None, "default", DEFAULT_MERMAID_THEME
        )
        assert "subgraph" in result or "Gateway" in result


# --- render_svg_output ---


class TestRenderSvgOutput:
    def test_basic_render(self):
        from unifi_network_maps.cli.render import render_svg_output

        args = _make_args(format="svg")
        devices = [
            _make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway"),
            _make_minimal_device("Switch", "aa:bb:cc:dd:ee:02", "switch"),
        ]
        topology = TopologyResult(
            tree_edges=[Edge("Gateway", "Switch")],
            raw_edges=[],
        )

        result = render_svg_output(
            args,
            devices,
            topology,
            config=None,
            site="default",
            svg_theme=DEFAULT_SVG_THEME,
        )
        assert result.startswith("<svg")

    def test_grouped_layout(self):
        from unifi_network_maps.cli.render import render_svg_output

        args = _make_args(format="svg", svg_layout_mode="grouped")
        devices = [
            _make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway"),
            _make_minimal_device("Switch", "aa:bb:cc:dd:ee:02", "switch"),
        ]
        topology = TopologyResult(
            tree_edges=[Edge("Gateway", "Switch")],
            raw_edges=[],
        )

        result = render_svg_output(args, devices, topology, None, "default", DEFAULT_SVG_THEME)
        assert "<svg" in result

    def test_grouped_layout_with_clients(self):
        from unifi_network_maps.cli.render import render_svg_output

        args = _make_args(format="svg", svg_layout_mode="grouped", include_clients=True)
        devices = [
            _make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway"),
            _make_minimal_device("Switch", "aa:bb:cc:dd:ee:02", "switch"),
        ]
        topology = TopologyResult(
            tree_edges=[Edge("Gateway", "Switch")],
            raw_edges=[],
        )
        mock_clients = [{"mac": "client:01", "name": "Laptop"}]

        result = render_svg_output(
            args,
            devices,
            topology,
            None,
            "default",
            DEFAULT_SVG_THEME,
            clients_override=mock_clients,  # type: ignore[arg-type]
        )
        assert "<svg" in result

    def test_collapse_clients(self):
        from unifi_network_maps.cli.render import render_svg_output

        args = _make_args(
            format="svg",
            svg_layout_mode="grouped",
            include_clients=True,
            collapse_clients=True,
        )
        devices = [_make_minimal_device("Switch", "aa:bb:cc:dd:ee:02", "switch")]
        topology = TopologyResult(
            tree_edges=[Edge("Switch", "Client1"), Edge("Switch", "Client2")],
            raw_edges=[],
        )
        mock_clients = [
            {"mac": "client:01", "name": "Client1"},
            {"mac": "client:02", "name": "Client2"},
        ]

        result = render_svg_output(
            args,
            devices,
            topology,
            None,
            "default",
            DEFAULT_SVG_THEME,
            clients_override=mock_clients,  # type: ignore[arg-type]
        )
        assert "<svg" in result

    def test_isometric_format(self):
        from unifi_network_maps.cli.render import render_svg_output

        args = _make_args(format="svg-iso")
        devices = [
            _make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway"),
            _make_minimal_device("Switch", "aa:bb:cc:dd:ee:02", "switch"),
        ]
        topology = TopologyResult(
            tree_edges=[Edge("Gateway", "Switch")],
            raw_edges=[],
        )

        result = render_svg_output(args, devices, topology, None, "default", DEFAULT_SVG_THEME)
        assert "<svg" in result
        assert "iso-node" in result


# --- render_standard_format ---


class TestRenderStandardFormat:
    def test_mermaid_format(self):
        from unifi_network_maps.cli.render import render_standard_format

        args = _make_args(format="mermaid", stdout=True)
        mock_devices = [
            {"name": "Gateway", "mac": "aa:bb:cc:dd:ee:01", "type": "gateway", "lldp_info": []},
            {"name": "Switch", "mac": "aa:bb:cc:dd:ee:02", "type": "switch", "lldp_info": []},
        ]

        result = render_standard_format(
            args,
            config=None,
            site="default",
            mock_devices=mock_devices,  # type: ignore[arg-type]
            mock_clients=None,
            mermaid_theme=DEFAULT_MERMAID_THEME,
            svg_theme=DEFAULT_SVG_THEME,
        )
        assert result == 0

    def test_svg_format(self):
        from unifi_network_maps.cli.render import render_standard_format

        args = _make_args(format="svg", stdout=True)
        mock_devices = [
            {"name": "Gateway", "mac": "aa:bb:cc:dd:ee:01", "type": "gateway", "lldp_info": []},
        ]

        result = render_standard_format(
            args,
            config=None,
            site="default",
            mock_devices=mock_devices,  # type: ignore[arg-type]
            mock_clients=None,
            mermaid_theme=DEFAULT_MERMAID_THEME,
            svg_theme=DEFAULT_SVG_THEME,
        )
        assert result == 0

    def test_svg_iso_format(self):
        from unifi_network_maps.cli.render import render_standard_format

        args = _make_args(format="svg-iso", stdout=True)
        mock_devices = [
            {"name": "Gateway", "mac": "aa:bb:cc:dd:ee:01", "type": "gateway", "lldp_info": []},
        ]

        result = render_standard_format(
            args,
            config=None,
            site="default",
            mock_devices=mock_devices,  # type: ignore[arg-type]
            mock_clients=None,
            mermaid_theme=DEFAULT_MERMAID_THEME,
            svg_theme=DEFAULT_SVG_THEME,
        )
        assert result == 0

    def test_unsupported_format(self, caplog):
        from unifi_network_maps.cli.render import render_standard_format

        args = _make_args(format="unsupported")
        mock_devices = [
            {"name": "Gateway", "mac": "aa:bb:cc:dd:ee:01", "type": "gateway", "lldp_info": []},
        ]

        import logging

        with caplog.at_level(logging.ERROR):
            result = render_standard_format(
                args,
                config=None,
                site="default",
                mock_devices=mock_devices,  # type: ignore[arg-type]
                mock_clients=None,
                mermaid_theme=DEFAULT_MERMAID_THEME,
                svg_theme=DEFAULT_SVG_THEME,
            )

        assert result == 2

    def test_topology_failure_returns_error(self, caplog):
        from unifi_network_maps.cli.render import render_standard_format

        args = _make_args(format="mermaid")
        mock_devices = [{"invalid": "data"}]

        import logging

        with caplog.at_level(logging.ERROR):
            result = render_standard_format(
                args,
                config=None,
                site="default",
                mock_devices=mock_devices,  # type: ignore[arg-type]
                mock_clients=None,
                mermaid_theme=DEFAULT_MERMAID_THEME,
                svg_theme=DEFAULT_SVG_THEME,
            )

        assert result == 1


# --- render_lldp_format ---


class TestRenderLldpFormat:
    def test_basic_render(self, capsys):
        from unifi_network_maps.cli.render import render_lldp_format

        args = _make_args(format="lldp-md", stdout=True)
        mock_devices = [
            {"name": "Switch", "mac": "aa:bb:cc:dd:ee:01", "type": "switch", "lldp_info": []},
        ]
        mock_clients = [{"mac": "client:01", "name": "Laptop"}]

        result = render_lldp_format(
            args,
            config=None,
            site="default",
            mock_devices=mock_devices,  # type: ignore[arg-type]
            mock_clients=mock_clients,  # type: ignore[arg-type]
        )
        assert result == 0

    def test_device_load_failure(self, caplog):
        from unifi_network_maps.cli.render import render_lldp_format

        args = _make_args(format="lldp-md")
        mock_devices = [{"invalid": "data"}]

        import logging

        with caplog.at_level(logging.ERROR):
            result = render_lldp_format(
                args,
                config=None,
                site="default",
                mock_devices=mock_devices,  # type: ignore[arg-type]
                mock_clients=[],
            )

        assert result == 1

    def test_missing_config_for_clients(self, caplog):
        from unifi_network_maps.cli.render import render_lldp_format

        args = _make_args(format="lldp-md")
        mock_devices = [
            {"name": "Switch", "mac": "aa:bb:cc:dd:ee:01", "type": "switch", "lldp_info": []},
        ]

        import logging

        with caplog.at_level(logging.ERROR):
            result = render_lldp_format(
                args,
                config=None,
                site="default",
                mock_devices=mock_devices,  # type: ignore[arg-type]
                mock_clients=None,  # No clients override, no config
            )

        assert result == 2


# --- render_mkdocs_format ---


class TestRenderMkdocsFormat:
    def test_sidebar_legend_requires_output(self, caplog):
        from unifi_network_maps.cli.render import render_mkdocs_format

        args = _make_args(format="mkdocs", mkdocs_sidebar_legend=True, output=None)
        devices = [_make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway")]
        topology = TopologyResult(tree_edges=[], raw_edges=[])

        import logging

        with caplog.at_level(logging.ERROR):
            result = render_mkdocs_format(
                args,
                devices=devices,
                topology=topology,
                config=None,
                site="default",
                mermaid_theme=DEFAULT_MERMAID_THEME,
                mock_clients=[],
            )

        assert result is None

    def test_client_ports_error(self, caplog):
        from unifi_network_maps.cli.render import render_mkdocs_format

        args = _make_args(format="mkdocs", include_clients=True)
        devices = [_make_minimal_device("Gateway", "aa:bb:cc:dd:ee:01", "gateway")]
        topology = TopologyResult(tree_edges=[], raw_edges=[])

        import logging

        with caplog.at_level(logging.ERROR):
            result = render_mkdocs_format(
                args,
                devices=devices,
                topology=topology,
                config=None,
                site="default",
                mermaid_theme=DEFAULT_MERMAID_THEME,
                mock_clients=None,  # Requires config
            )

        assert result is None
