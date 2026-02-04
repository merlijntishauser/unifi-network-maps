"""Shared device summary helpers for markdown renderers."""

from __future__ import annotations

from ..model.topology import Device, PortInfo, classify_device_type


def port_summary(device: Device) -> str:
    """Summarize port count and activity for a device."""
    ports = [port for port in device.port_table if port.port_idx is not None]
    if not ports:
        return "-"
    total_ports = len(ports)
    active_ports = sum(1 for port in ports if (port.speed or 0) > 0)
    return f"{total_ports} total, {active_ports} active"


def poe_summary(device: Device) -> str:
    """Summarize PoE capability, activity, and power draw."""
    ports = [port for port in device.port_table if port.port_idx is not None]
    if not ports:
        return "-"
    poe_capable = sum(1 for port in ports if port.port_poe or port.poe_enable)
    poe_active = sum(1 for port in ports if _is_poe_active(port))
    total_power = sum(port.poe_power or 0.0 for port in ports)
    summary = f"{poe_capable} capable, {poe_active} active"
    if total_power > 0:
        summary = f"{summary}, {total_power:.2f}W"
    return summary


def uplink_summary(device: Device) -> str:
    """Describe the device's uplink connection."""
    uplink = device.uplink or device.last_uplink
    if not uplink:
        if classify_device_type(device) == "gateway":
            return "Internet"
        return "-"
    name = uplink.name or uplink.mac or "Unknown"
    if classify_device_type(device) == "gateway":
        lowered = name.lower()
        if lowered in {"unknown", "wan", "internet"}:
            name = "Internet"
        elif lowered.startswith(("eth", "wan")):
            name = "Internet"
    if uplink.port is not None:
        return f"{name} (Port {uplink.port})"
    return name


def _is_poe_active(port: PortInfo) -> bool:
    return (port.poe_power or 0.0) > 0 or port.poe_good
