"""Text formatting and label utilities for SVG rendering."""

from __future__ import annotations

from ..model.topology import WanInfo, WanInterface


def _escape_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _extract_port_text(side: str) -> str | None:
    candidate = side.split(":", 1)[1].strip() if ":" in side else side.strip()
    if candidate.lower().startswith("port "):
        return candidate
    return None


def _extract_device_name(side: str) -> str | None:
    if ":" not in side:
        return None
    name = side.split(":", 1)[0].strip()
    return name or None


def _strip_local_port(label: str, node_type: str) -> str:
    """Strip the local port from a bidirectional label for single-port devices (APs)."""
    if node_type == "ap" and "<->" in label:
        return label.split("<->", 1)[0].strip()
    return label


def _format_compact_ports(
    left_name: str | None,
    left_port: str | None,
    right_port: str | None,
    label: str,
) -> str:
    if left_port and right_port:
        if left_name:
            return f"{left_name} {left_port} <-> {right_port}"
        return f"{left_port} <-> {right_port}"
    return left_port or right_port or label


def _compact_edge_label(
    label: str, *, left_node: str | None = None, right_node: str | None = None
) -> str:
    if "<->" not in label:
        return label
    left_segment, right_segment = (part.strip() for part in label.split("<->", 1))
    left_name = _extract_device_name(left_segment)
    right_name = _extract_device_name(right_segment)
    left_port = _extract_port_text(left_segment)
    right_port = _extract_port_text(right_segment)
    if left_node and right_node:
        if right_name and right_name == left_node and left_name == right_node:
            left_name, right_name = right_name, left_name
            left_port, right_port = right_port, left_port
    return _format_compact_ports(left_name, left_port, right_port, label)


def _format_port_label_lines(
    port_label: str,
    *,
    prefix: str,
    max_chars: int,
) -> list[str]:
    def _port_only(segment: str) -> str:
        port = _extract_port_text(segment)
        if port:
            return port
        lower = segment.lower()
        idx = lower.rfind("port ")
        if idx != -1:
            return segment[idx:].strip()
        return segment.split(":", 1)[-1].strip()

    def _truncate(text: str, max_len: int = max_chars) -> str:
        return text[: max_len - 3].rstrip() + "..." if len(text) > max_len else text

    if "<->" in port_label:
        left_part, right_part = (part.strip() for part in port_label.split("<->", 1))
        front_text = _truncate(f"{prefix}: {_port_only(left_part)}")
        side_text = _truncate(f"local: {_port_only(right_part)}")
        return [line for line in (front_text, side_text) if line]
    side_text = _truncate(f"{prefix}: {_port_only(port_label)}")
    return [side_text]


def _wrap_text(label: str, *, max_len: int = 24) -> list[str]:
    if len(label) <= max_len:
        return [label]
    split_at = label.rfind(" ", 0, max_len + 1)
    if split_at == -1:
        split_at = max_len
    first = label[:split_at].rstrip()
    rest = label[split_at:].lstrip()
    return [first, rest] if rest else [first]


def _shorten_prefix(name: str, max_words: int = 2) -> str:
    words = name.split()
    if len(words) <= max_words:
        return name
    return " ".join(words[:max_words]) + "..."


def _label_metrics(
    lines: list[str], *, font_size: int, padding_x: int = 6, padding_y: int = 3
) -> tuple[float, float]:
    max_len = max((len(line) for line in lines), default=0)
    text_width = max_len * font_size * 0.6
    text_height = len(lines) * (font_size + 2)
    width = text_width + padding_x * 2
    height = text_height + padding_y * 2
    return width, height


def _format_wan_speed(speed_mbps: int | None) -> str | None:
    """Format speed in Mbps to human-readable string (e.g., 10GbE, 100MbE)."""
    if speed_mbps is None or speed_mbps == 0:
        return None
    if speed_mbps >= 1000:
        gbps = speed_mbps / 1000
        if gbps == int(gbps):
            return f"{int(gbps)}GbE"
        return f"{gbps:.1f}GbE"
    return f"{speed_mbps}MbE"


def _format_wan_interface_line(
    wan: WanInterface,
    prefix: str,
    *,
    is_dual: bool,
    include_speed: bool = True,
) -> str:
    """Format a single WAN interface line."""
    status = "(active)" if wan.enabled else "(disabled)"
    label = wan.label or prefix
    speed_parts = []
    if include_speed and wan.link_speed and wan.enabled:
        speed_parts.append(f"Link {_format_wan_speed(wan.link_speed)}")
    if wan.isp_speed:
        speed_parts.append(f"ISP {wan.isp_speed}")
    speed_str = " / ".join(speed_parts) if speed_parts else ""

    if not wan.enabled and prefix == "WAN2":
        return f"{prefix}: {label} (disabled)"

    if is_dual:
        line = f"{prefix}: {label}"
        if speed_str:
            line += f" ({speed_str})"
        return f"{line} {status}"

    return label


def _build_wan_label_lines(wan_info: WanInfo) -> list[str]:
    """Build label lines for WAN display."""
    label_lines: list[str] = []
    is_dual = wan_info.wan2 is not None

    if wan_info.wan1:
        wan1 = wan_info.wan1
        if is_dual:
            label_lines.append(
                _format_wan_interface_line(wan1, "WAN1", is_dual=True, include_speed=True)
            )
        else:
            # Single WAN format: multi-line
            label_lines.append(wan1.label or "WAN1")
            speed_parts = []
            if wan1.link_speed:
                speed_parts.append(f"Link {_format_wan_speed(wan1.link_speed)}")
            if wan1.isp_speed:
                speed_parts.append(f"ISP {wan1.isp_speed}")
            if speed_parts:
                label_lines.append(" / ".join(speed_parts))
            if wan1.ip_address:
                label_lines.append(wan1.ip_address)

    if wan_info.wan2:
        label_lines.append(
            _format_wan_interface_line(wan_info.wan2, "WAN2", is_dual=True, include_speed=True)
        )
        # Add IP from WAN1 for dual WAN display
        if wan_info.wan1 and wan_info.wan1.ip_address:
            label_lines.append(wan_info.wan1.ip_address)

    return label_lines
