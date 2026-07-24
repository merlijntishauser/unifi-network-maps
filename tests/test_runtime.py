"""Tests for CLI runtime data preparation."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

import pytest
from unifi_topology.model.topology import Device, Edge, TopologyResult, UplinkInfo

from unifi_network_maps.cli.runtime import (
    build_edges_with_clients,
    load_dark_mermaid_theme,
    load_devices_data,
    load_topology_for_render,
    resolve_mkdocs_client_ports,
    select_edges,
)

pytestmark = pytest.mark.integration


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
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# --- load_devices_data ---


class TestLoadDevicesData:
    def test_with_override(self):
        """Test loading devices with raw_devices_override."""
        raw_devices = [
            {"name": "Switch1", "mac": "aa:bb:cc:dd:ee:01", "lldp_info": []},
        ]
        args = _make_args()
        _raw, devices = load_devices_data(
            args,
            config=None,
            site="default",
            raw_devices_override=raw_devices,  # type: ignore[arg-type]
        )
        assert len(devices) == 1
        assert devices[0].name == "Switch1"

    def test_config_required_without_override(self):
        """Test that config is required when no override provided."""
        args = _make_args()
        with pytest.raises(ValueError, match="Config required"):
            load_devices_data(args, config=None, site="default")

    def test_networks_fetch_exception_logs_debug(self, caplog):
        """Test that network fetch failures are logged but don't crash."""
        raw_devices = [
            {"name": "Switch1", "mac": "aa:bb:cc:dd:ee:01", "lldp_info": []},
        ]
        args = _make_args()
        mock_config = MagicMock()

        with patch(
            "unifi_network_maps.cli.runtime.fetch_networks",
            side_effect=Exception("Network error"),
        ):
            import logging

            with caplog.at_level(logging.DEBUG):
                _raw, devices = load_devices_data(
                    args,
                    config=mock_config,
                    site="default",
                    raw_devices_override=raw_devices,  # type: ignore[arg-type]
                )
                # Should still succeed with devices
                assert len(devices) == 1


# --- build_edges_with_clients ---


class TestBuildEdgesWithClients:
    def test_without_clients(self):
        """Test building edges without client inclusion."""
        args = _make_args(include_clients=False)
        devices = [_make_minimal_device("Switch", "aa:bb:cc:dd:ee:ff")]
        edges = [Edge("Gateway", "Switch")]

        result_edges, clients = build_edges_with_clients(
            args,
            edges,
            devices,
            config=None,
            site="default",
        )
        assert clients is None
        assert len(result_edges) == 1

    def test_with_clients_override(self):
        """Test building edges with clients_override."""
        args = _make_args(include_clients=True)
        devices = [_make_minimal_device("Switch", "aa:bb:cc:dd:ee:ff")]
        edges = [Edge("Gateway", "Switch")]
        clients_data = [{"mac": "client:01", "name": "Laptop"}]

        _result_edges, clients = build_edges_with_clients(
            args,
            edges,
            devices,
            config=None,
            site="default",
            clients_override=clients_data,  # type: ignore[arg-type]
        )
        assert clients is not None
        assert len(clients) == 1

    def test_config_required_for_clients(self):
        """Test that config is required when fetching clients."""
        args = _make_args(include_clients=True)
        devices = [_make_minimal_device("Switch", "aa:bb:cc:dd:ee:ff")]
        edges = []

        with pytest.raises(ValueError, match="Config required"):
            build_edges_with_clients(
                args,
                edges,
                devices,
                config=None,
                site="default",
            )


# --- select_edges ---


class TestSelectEdges:
    def test_prefers_tree_edges(self):
        """Test that tree_edges are preferred when available."""
        topology = TopologyResult(
            tree_edges=[Edge("A", "B")],
            raw_edges=[Edge("X", "Y")],
        )
        edges, has_tree = select_edges(topology)
        assert has_tree is True
        assert len(edges) == 1
        assert edges[0].left == "A"

    def test_falls_back_to_raw_edges(self, caplog):
        """Test fallback to raw_edges when no tree_edges."""
        topology = TopologyResult(
            tree_edges=[],
            raw_edges=[Edge("X", "Y")],
        )

        import logging

        with caplog.at_level(logging.WARNING):
            edges, has_tree = select_edges(topology)

        assert has_tree is False
        assert len(edges) == 1
        assert edges[0].left == "X"


# --- load_topology_for_render ---


class TestLoadTopologyForRender:
    def test_success_returns_devices_and_topology(self):
        """Test successful topology loading."""
        args = _make_args()
        mock_devices = [
            {"name": "Gateway", "mac": "aa:bb:cc:dd:ee:01", "type": "gateway", "lldp_info": []},
            {"name": "Switch", "mac": "aa:bb:cc:dd:ee:02", "type": "switch", "lldp_info": []},
        ]

        result = load_topology_for_render(
            args,
            config=None,
            site="default",
            mock_devices=mock_devices,  # type: ignore[arg-type]
        )
        assert result is not None
        devices, _ = result
        assert len(devices) == 2

    def test_failure_returns_none(self, caplog):
        """Test that errors return None and log error."""
        args = _make_args()
        mock_devices = [{"invalid": "data"}]

        import logging

        with patch(
            "unifi_network_maps.cli.runtime.build_topology_data",
            side_effect=Exception("Topology error"),
        ):
            with caplog.at_level(logging.ERROR):
                result = load_topology_for_render(
                    args,
                    config=None,
                    site="default",
                    mock_devices=mock_devices,  # type: ignore[arg-type]
                )

        assert result is None
        assert "Failed to build topology" in caplog.text


# --- load_dark_mermaid_theme ---


class TestLoadDarkMermaidTheme:
    def test_loads_dark_theme(self):
        """Test that dark theme is loaded successfully."""
        theme = load_dark_mermaid_theme()
        assert theme is not None

    def test_returns_none_on_error(self, caplog):
        """Test that None is returned on load failure."""
        import logging

        with patch(
            "unifi_network_maps.cli.runtime.resolve_themes",
            side_effect=ValueError("Load error"),
        ):
            with caplog.at_level(logging.WARNING):
                theme = load_dark_mermaid_theme()

        assert theme is None


# --- resolve_mkdocs_client_ports ---


class TestResolveMkdocsClientPorts:
    def test_without_clients(self):
        """Test that None is returned when clients not included."""
        args = _make_args(include_clients=False)
        devices = []

        client_ports, error = resolve_mkdocs_client_ports(
            args,
            devices,
            config=None,
            site="default",
            mock_clients=None,
        )
        assert client_ports is None
        assert error is None

    def test_with_mock_clients(self):
        """Test with mock clients data."""
        args = _make_args(include_clients=True)
        devices = [_make_minimal_device("Switch", "aa:bb:cc:dd:ee:ff")]
        mock_clients = [
            {"mac": "client:01", "name": "Laptop", "sw_mac": "aa:bb:cc:dd:ee:ff", "sw_port": 1}
        ]

        _, error = resolve_mkdocs_client_ports(
            args,
            devices,
            config=None,
            site="default",
            mock_clients=mock_clients,  # type: ignore[arg-type]
        )
        assert error is None

    def test_config_required_error(self):
        """Test that error code 2 is returned when config missing."""
        args = _make_args(include_clients=True)
        devices = []

        client_ports, error = resolve_mkdocs_client_ports(
            args,
            devices,
            config=None,
            site="default",
            mock_clients=None,
        )
        assert client_ports is None
        assert error == 2
