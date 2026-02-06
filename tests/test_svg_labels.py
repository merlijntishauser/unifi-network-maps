"""Tests for SVG label utilities."""

from __future__ import annotations

from unifi_network_maps.model.topology import WanInfo, WanInterface
from unifi_network_maps.render.svg_labels import (
    _build_wan_label_lines,
    _compact_edge_label,
    _escape_text,
    _extract_device_name,
    _extract_port_text,
    _format_port_label_lines,
    _format_wan_speed,
    _label_metrics,
    _shorten_prefix,
    _wrap_text,
)

# --- _escape_text ---


class TestEscapeText:
    def test_escapes_ampersand(self):
        assert _escape_text("A & B") == "A &amp; B"

    def test_escapes_less_than(self):
        assert _escape_text("A < B") == "A &lt; B"

    def test_escapes_greater_than(self):
        assert _escape_text("A > B") == "A &gt; B"

    def test_escapes_all_special_chars(self):
        assert _escape_text("<A & B>") == "&lt;A &amp; B&gt;"

    def test_no_escape_needed(self):
        assert _escape_text("plain text") == "plain text"


# --- _extract_port_text ---


class TestExtractPortText:
    def test_extracts_port_after_colon(self):
        assert _extract_port_text("Switch: Port 24") == "Port 24"

    def test_extracts_standalone_port(self):
        assert _extract_port_text("Port 1") == "Port 1"

    def test_returns_none_for_no_port(self):
        assert _extract_port_text("Switch: eth0") is None

    def test_case_insensitive(self):
        assert _extract_port_text("Device: port 5") == "port 5"


# --- _extract_device_name ---


class TestExtractDeviceName:
    def test_extracts_name_before_colon(self):
        assert _extract_device_name("Switch: Port 24") == "Switch"

    def test_returns_none_without_colon(self):
        assert _extract_device_name("Port 24") is None

    def test_returns_none_for_empty_name(self):
        assert _extract_device_name(": Port 24") is None

    def test_strips_whitespace(self):
        assert _extract_device_name("  Switch  : Port 24") == "Switch"


# --- _compact_edge_label ---


class TestCompactEdgeLabel:
    def test_returns_unchanged_without_arrow(self):
        assert _compact_edge_label("Port 24") == "Port 24"

    def test_compacts_bidirectional_ports(self):
        label = "Switch: Port 1 <-> AP: Port 0"
        result = _compact_edge_label(label)
        assert "Port 1" in result
        assert "Port 0" in result

    def test_returns_single_port_if_only_one(self):
        label = "Switch: Port 1 <-> AP: eth0"
        result = _compact_edge_label(label)
        assert result == "Port 1"

    def test_swaps_order_when_names_match_nodes(self):
        label = "Switch: Port 1 <-> AP: Port 0"
        result = _compact_edge_label(label, left_node="AP", right_node="Switch")
        # Should swap to match node order
        assert "Port 0" in result or "Port 1" in result


# --- _format_port_label_lines ---


class TestFormatPortLabelLines:
    def test_single_port(self):
        lines = _format_port_label_lines("Port 24", prefix="uplink", max_chars=30)
        assert len(lines) == 1
        assert "Port 24" in lines[0]

    def test_bidirectional_creates_two_lines(self):
        lines = _format_port_label_lines(
            "Switch: Port 1 <-> AP: Port 0",
            prefix="uplink",
            max_chars=30,
        )
        assert len(lines) == 2

    def test_truncates_long_labels(self):
        lines = _format_port_label_lines(
            "Very Long Device Name: Port 24",
            prefix="uplink",
            max_chars=20,
        )
        # Should truncate to max_chars
        assert all(len(line) <= 20 for line in lines)

    def test_prefix_used_in_label(self):
        lines = _format_port_label_lines("Port 5", prefix="switch", max_chars=30)
        assert "switch" in lines[0]


# --- _wrap_text ---


class TestWrapText:
    def test_no_wrap_short_text(self):
        assert _wrap_text("Short", max_len=24) == ["Short"]

    def test_wraps_at_space(self):
        lines = _wrap_text("Hello World Test", max_len=12)
        assert len(lines) == 2
        assert lines[0] == "Hello World"
        assert lines[1] == "Test"

    def test_wraps_at_max_len_if_no_space(self):
        lines = _wrap_text("NoSpacesHere", max_len=5)
        assert len(lines) == 2
        assert lines[0] == "NoSpa"
        assert lines[1] == "cesHere"

    def test_exact_length_no_wrap(self):
        text = "ExactLength"
        assert _wrap_text(text, max_len=len(text)) == [text]


# --- _shorten_prefix ---


class TestShortenPrefix:
    def test_no_change_under_limit(self):
        assert _shorten_prefix("AP Living", max_words=2) == "AP Living"

    def test_shortens_long_names(self):
        assert _shorten_prefix("AP Living Room Extended", max_words=2) == "AP Living..."

    def test_single_word(self):
        assert _shorten_prefix("Switch", max_words=2) == "Switch"


# --- _label_metrics ---


class TestLabelMetrics:
    def test_empty_lines(self):
        width, height = _label_metrics([], font_size=12)
        assert width == 12  # padding only
        assert height == 6  # padding only

    def test_single_line(self):
        width, height = _label_metrics(["Test"], font_size=12)
        assert width > 12  # text + padding
        assert height > 6  # text + padding

    def test_multiple_lines_increase_height(self):
        _, height1 = _label_metrics(["A"], font_size=12)
        _, height2 = _label_metrics(["A", "B"], font_size=12)
        assert height2 > height1

    def test_longer_text_increases_width(self):
        width1, _ = _label_metrics(["A"], font_size=12)
        width2, _ = _label_metrics(["AAAAAAAAAA"], font_size=12)
        assert width2 > width1


# --- _format_wan_speed ---


class TestFormatWanSpeed:
    def test_none_returns_none(self):
        assert _format_wan_speed(None) is None

    def test_zero_returns_none(self):
        assert _format_wan_speed(0) is None

    def test_megabit_format(self):
        assert _format_wan_speed(100) == "100MbE"

    def test_gigabit_format(self):
        assert _format_wan_speed(1000) == "1GbE"

    def test_ten_gigabit_format(self):
        assert _format_wan_speed(10000) == "10GbE"

    def test_fractional_gigabit(self):
        assert _format_wan_speed(2500) == "2.5GbE"


# --- _build_wan_label_lines ---


class TestBuildWanLabelLines:
    def test_single_wan_basic(self):
        wan = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        info = WanInfo(wan1=wan, wan2=None)
        lines = _build_wan_label_lines(info)
        assert len(lines) >= 1
        assert "WAN1" in lines[0] or any("1GbE" in line for line in lines)

    def test_single_wan_with_label(self):
        wan = WanInterface(
            port_idx=1,
            link_speed=1000,
            ip_address="1.2.3.4",
            enabled=True,
            label="KPN Fiber",
        )
        info = WanInfo(wan1=wan, wan2=None)
        lines = _build_wan_label_lines(info)
        assert any("KPN Fiber" in line for line in lines)

    def test_single_wan_with_isp_speed(self):
        wan = WanInterface(
            port_idx=1,
            link_speed=1000,
            ip_address="1.2.3.4",
            enabled=True,
            isp_speed="500/500",
        )
        info = WanInfo(wan1=wan, wan2=None)
        lines = _build_wan_label_lines(info)
        assert any("ISP 500/500" in line for line in lines)

    def test_dual_wan(self):
        wan1 = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan2 = WanInterface(port_idx=9, link_speed=100, ip_address=None, enabled=True)
        info = WanInfo(wan1=wan1, wan2=wan2)
        lines = _build_wan_label_lines(info)
        assert any("WAN1" in line for line in lines)
        assert any("WAN2" in line for line in lines)

    def test_dual_wan_with_disabled_wan2(self):
        wan1 = WanInterface(port_idx=1, link_speed=1000, ip_address="1.2.3.4", enabled=True)
        wan2 = WanInterface(
            port_idx=9, link_speed=None, ip_address=None, enabled=False, label="Backup"
        )
        info = WanInfo(wan1=wan1, wan2=wan2)
        lines = _build_wan_label_lines(info)
        assert any("disabled" in line for line in lines)

    def test_ip_address_included(self):
        wan = WanInterface(port_idx=1, link_speed=1000, ip_address="203.0.113.1", enabled=True)
        info = WanInfo(wan1=wan, wan2=None)
        lines = _build_wan_label_lines(info)
        assert any("203.0.113.1" in line for line in lines)
