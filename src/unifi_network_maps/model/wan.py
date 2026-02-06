"""WAN interface extraction from gateway devices."""

from __future__ import annotations

from .classify import classify_device_type
from .topology import Device, PortInfo, WanInfo, WanInterface


def _normalize_wan_speed(speed: int | None) -> int | None:
    """Normalize WAN port speed to Mbps.

    Gateway devices report WAN port speeds in Gbps (e.g., 10 for 10G),
    while switches report in Mbps (e.g., 1000 for 1G).
    """
    if speed is None or speed == 0:
        return speed
    if 1 <= speed <= 100:
        return speed * 1000
    return speed


def _find_wan_port_by_assignment(port_table: list[PortInfo], wan_id: str) -> PortInfo | None:
    """Find a WAN port by its wan_networkconf_id assignment."""
    wan_id_lower = wan_id.lower()
    for port in port_table:
        if port.wan_networkconf_id:
            conf_id = port.wan_networkconf_id.lower()
            if conf_id == wan_id_lower or wan_id_lower in conf_id:
                return port
    return None


def _find_wan_port_by_idx(port_table: list[PortInfo], port_idx: int) -> PortInfo | None:
    """Find a port by index (fallback for legacy detection)."""
    for port in port_table:
        if port.port_idx == port_idx:
            return port
    return None


def _find_wan1_port(port_table: list[PortInfo]) -> PortInfo | None:
    """Find WAN1 port by assignment, falling back to port 1."""
    port = _find_wan_port_by_assignment(port_table, "WAN")
    if not port:
        port = _find_wan_port_by_assignment(port_table, "WAN1")
    if not port:
        port = _find_wan_port_by_idx(port_table, 1)
    return port


def _find_wan2_port(port_table: list[PortInfo]) -> PortInfo | None:
    """Find WAN2 port by assignment, falling back to port 9 or 2."""
    port = _find_wan_port_by_assignment(port_table, "WAN2")
    if not port:
        port = _find_wan_port_by_idx(port_table, 9)
    if not port:
        port = _find_wan_port_by_idx(port_table, 2)
    return port


def _build_wan_interface(
    port: PortInfo,
    default_idx: int,
    ip_address: str | None,
    label: str | None,
    isp_speed: str | None,
    *,
    enabled_override: bool | None = None,
) -> WanInterface:
    """Build a WAN interface from port info."""
    speed = _normalize_wan_speed(port.speed)
    if enabled_override is not None:
        enabled = enabled_override
    else:
        enabled = speed is not None and speed > 0
    return WanInterface(
        port_idx=port.port_idx or default_idx,
        link_speed=speed,
        ip_address=ip_address,
        enabled=enabled,
        label=label,
        isp_speed=isp_speed,
    )


def _should_include_wan2(
    port: PortInfo | None,
    label: str | None,
    isp_speed: str | None,
) -> bool:
    """Determine if WAN2 should be included in the output."""
    if not port:
        return False
    has_assignment = port.wan_networkconf_id is not None
    has_cli_config = label is not None or isp_speed is not None
    speed = _normalize_wan_speed(port.speed)
    is_active = speed is not None and speed > 0
    return has_assignment or has_cli_config or is_active


def _resolve_wan2_enabled(
    wan2_disabled: str,
    wan_enabled_map: dict[str, bool] | None,
) -> bool | None:
    """Resolve the WAN2 enabled state from CLI override and network config.

    Returns True/False for explicit state, or None for speed-based fallback.
    """
    if wan2_disabled == "true":
        return False
    if wan2_disabled == "false":
        return True
    if wan_enabled_map and "wan2" in wan_enabled_map:
        return wan_enabled_map["wan2"]
    return None


def extract_wan_info(
    device: Device,
    *,
    wan1_label: str | None = None,
    wan1_isp_speed: str | None = None,
    wan2_label: str | None = None,
    wan2_isp_speed: str | None = None,
    wan_enabled_map: dict[str, bool] | None = None,
    wan2_disabled: str = "auto",
) -> WanInfo | None:
    """Extract WAN interface information from a gateway device.

    Detects WAN ports by their wan_networkconf_id assignment field. Falls back
    to legacy port number detection (port 1 for WAN1, port 9/2 for WAN2) if
    no WAN assignment is found.

    The ``wan2_disabled`` parameter accepts ``"auto"``, ``"true"``, or
    ``"false"`` to override WAN2 enabled detection.  When ``"auto"``, the
    ``wan_enabled_map`` (built from network configs) is consulted first,
    falling back to speed-based detection.
    """
    if classify_device_type(device) != "gateway":
        return None
    if not device.port_table:
        return None

    wan1_port = _find_wan1_port(device.port_table)
    wan1 = None
    if wan1_port:
        wan1 = _build_wan_interface(wan1_port, 1, device.ip, wan1_label, wan1_isp_speed)

    wan2_port = _find_wan2_port(device.port_table)
    wan2 = None
    if _should_include_wan2(wan2_port, wan2_label, wan2_isp_speed):
        wan2_enabled = _resolve_wan2_enabled(wan2_disabled, wan_enabled_map)
        wan2 = _build_wan_interface(
            wan2_port,  # type: ignore[arg-type]
            9,
            None,
            wan2_label,
            wan2_isp_speed,
            enabled_override=wan2_enabled,
        )

    if wan1 or wan2:
        return WanInfo(wan1=wan1, wan2=wan2)
    return None
