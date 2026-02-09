"""Tests for reverse DNS hostname resolution."""

from unittest.mock import MagicMock, patch

from unifi_network_maps.adapters.dns import resolve_hostnames


def test_resolve_hostnames_success():
    mock_answer = MagicMock()
    mock_answer.__getitem__ = MagicMock(return_value="switch1.local.")

    with (
        patch("unifi_network_maps.adapters.dns.dns.resolver.Resolver") as mock_resolver_cls,
        patch("unifi_network_maps.adapters.dns.dns.reversename.from_address") as mock_from_addr,
    ):
        mock_resolver = MagicMock()
        mock_resolver_cls.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_answer
        mock_from_addr.return_value = "10.1.168.192.in-addr.arpa."

        result = resolve_hostnames(["192.168.1.10"], "192.168.1.1")

    assert result == {"192.168.1.10": "switch1.local"}


def test_resolve_hostnames_failure_skipped():
    with (
        patch("unifi_network_maps.adapters.dns.dns.resolver.Resolver") as mock_resolver_cls,
        patch("unifi_network_maps.adapters.dns.dns.reversename.from_address"),
    ):
        mock_resolver = MagicMock()
        mock_resolver_cls.return_value = mock_resolver
        mock_resolver.resolve.side_effect = Exception("NXDOMAIN")

        result = resolve_hostnames(["192.168.1.10"], "192.168.1.1")

    assert result == {}


def test_resolve_hostnames_partial():
    """One IP resolves, the other fails."""
    mock_answer = MagicMock()
    mock_answer.__getitem__ = MagicMock(return_value="gw.local.")

    with (
        patch("unifi_network_maps.adapters.dns.dns.resolver.Resolver") as mock_resolver_cls,
        patch("unifi_network_maps.adapters.dns.dns.reversename.from_address"),
    ):
        mock_resolver = MagicMock()
        mock_resolver_cls.return_value = mock_resolver

        def side_effect(*_args, **_kwargs):
            if mock_resolver.resolve.call_count == 1:
                return mock_answer
            raise Exception("NXDOMAIN")

        mock_resolver.resolve.side_effect = side_effect

        result = resolve_hostnames(["192.168.1.1", "192.168.1.10"], "192.168.1.1")

    assert "192.168.1.1" in result
    assert result["192.168.1.1"] == "gw.local"
    assert "192.168.1.10" not in result


def test_resolve_hostnames_strips_trailing_dot():
    mock_answer = MagicMock()
    mock_answer.__getitem__ = MagicMock(return_value="host.example.com.")

    with (
        patch("unifi_network_maps.adapters.dns.dns.resolver.Resolver") as mock_resolver_cls,
        patch("unifi_network_maps.adapters.dns.dns.reversename.from_address"),
    ):
        mock_resolver = MagicMock()
        mock_resolver_cls.return_value = mock_resolver
        mock_resolver.resolve.return_value = mock_answer

        result = resolve_hostnames(["10.0.0.1"], "10.0.0.1")

    assert result["10.0.0.1"] == "host.example.com"


def test_resolve_hostnames_empty_list():
    result = resolve_hostnames([], "192.168.1.1")
    assert result == {}


def test_resolve_hostnames_sets_nameserver():
    with (
        patch("unifi_network_maps.adapters.dns.dns.resolver.Resolver") as mock_resolver_cls,
        patch("unifi_network_maps.adapters.dns.dns.reversename.from_address"),
    ):
        mock_resolver = MagicMock()
        mock_resolver_cls.return_value = mock_resolver
        mock_resolver.resolve.side_effect = Exception("fail")

        resolve_hostnames(["192.168.1.10"], "10.0.0.53")

    assert mock_resolver.nameservers == ["10.0.0.53"]
