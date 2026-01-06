"""Render per-device port overview tables."""

from __future__ import annotations

from collections import defaultdict

from ..model.ports import extract_port_number
from ..model.topology import ClientPortMap, Device, PortMap, classify_device_type


def render_device_port_overview(
    devices: list[Device],
    port_map: PortMap,
    *,
    client_ports: ClientPortMap | None = None,
) -> str:
    gateways = _collect_devices_by_type(devices, "gateway")
    switches = _collect_devices_by_type(devices, "switch")
    lines: list[str] = []
    if gateways:
        lines.append("## Gateways")
        lines.append("")
        lines.extend(_render_device_group(gateways, port_map, client_ports))
    if switches:
        if lines:
            lines.append("")
        lines.append("## Switches")
        lines.append("")
        lines.extend(_render_device_group(switches, port_map, client_ports))
    return "\n".join(lines).rstrip() + "\n"


def _collect_devices_by_type(devices: list[Device], desired_type: str) -> list[Device]:
    return sorted(
        [device for device in devices if classify_device_type(device) == desired_type],
        key=lambda item: item.name.lower(),
    )


def _render_device_group(
    devices: list[Device],
    port_map: PortMap,
    client_ports: ClientPortMap | None,
) -> list[str]:
    lines: list[str] = []
    for device in devices:
        lines.append(f"### {device.name}")
        lines.append("")
        lines.extend(_render_device_details(device))
        lines.extend(_render_device_ports(device, port_map, client_ports))
        lines.append("")
    return lines


def _render_device_ports(
    device: Device,
    port_map: PortMap,
    client_ports: ClientPortMap | None,
) -> list[str]:
    rows = _build_port_rows(device, port_map, client_ports)
    lines = [
        "#### Ports",
        "",
        "| Port | Connected | Speed | PoE | Power |",
        "| --- | --- | --- | --- | --- |",
    ]
    for port_label, connected, speed, poe_state, power in rows:
        lines.append(
            f"| {_escape_cell(port_label)} | {_escape_cell(connected or '-')} | "
            f"{_escape_cell(speed)} | {_escape_cell(poe_state)} | {_escape_cell(power)} |"
        )
    return lines


def _build_port_rows(
    device: Device,
    port_map: PortMap,
    client_ports: ClientPortMap | None,
) -> list[tuple[str, str, str, str, str]]:
    connections = _device_port_connections(device.name, port_map)
    client_connections = _device_client_connections(device.name, client_ports)
    rows: list[tuple[str, str, str, str, str]] = []
    seen_ports: set[int] = set()
    for port in sorted(device.port_table, key=_port_sort_key):
        port_idx = _port_index(port.port_idx, port.name)
        if port_idx is not None:
            seen_ports.add(port_idx)
        port_label = _format_port_label(port_idx, port.name)
        connected = _format_connections(
            device.name,
            port_idx,
            connections,
            client_connections,
            port_map,
        )
        rows.append(
            (
                port_label,
                connected,
                _format_speed(port.speed),
                _format_poe_state(device, port),
                _format_poe_power(port.poe_power),
            )
        )
    for port_idx in sorted(connections):
        if port_idx in seen_ports:
            continue
        port_label = _format_port_label(port_idx, None)
        connected = _format_connections(
            device.name,
            port_idx,
            connections,
            client_connections,
            port_map,
        )
        rows.append(
            (
                port_label,
                connected,
                "-",
                "-",
                "-",
            )
        )
    return rows


def _device_port_connections(device_name: str, port_map: PortMap) -> dict[int, list[str]]:
    connections: dict[int, list[str]] = defaultdict(list)
    for (src, dst), label in port_map.items():
        if src != device_name:
            continue
        port_idx = extract_port_number(label or "")
        if port_idx is None:
            continue
        connections[port_idx].append(dst)
    return connections


def _device_client_connections(
    device_name: str, client_ports: ClientPortMap | None
) -> dict[int, list[str]]:
    if not client_ports:
        return {}
    rows = client_ports.get(device_name, [])
    connections: dict[int, list[str]] = defaultdict(list)
    for port_idx, name in rows:
        connections[port_idx].append(name)
    return connections


def _format_connections(
    device_name: str,
    port_idx: int | None,
    connections: dict[int, list[str]],
    client_connections: dict[int, list[str]],
    port_map: PortMap,
) -> str:
    if port_idx is None:
        return ""
    peers = connections.get(port_idx, [])
    clients = client_connections.get(port_idx, [])
    if not peers and not clients:
        return ""
    rendered: list[str] = []
    for peer in sorted(peers, key=str.lower):
        peer_label = port_map.get((peer, device_name))
        if peer_label:
            rendered.append(f"{peer} ({peer_label})")
        else:
            rendered.append(peer)
    for client_name in sorted(clients, key=str.lower):
        rendered.append(f"{client_name} (client)")
    return ", ".join(rendered)


def _format_port_label(port_idx: int | None, name: str | None) -> str:
    if port_idx is None and name:
        return name
    if port_idx is None:
        return "Port ?"
    base = f"Port {port_idx}"
    if name and name.strip() and name.strip() != base:
        return f"{base} ({name.strip()})"
    return base


def _format_speed(speed: int | None) -> str:
    if speed is None or speed <= 0:
        return "-"
    if speed % 1000 == 0:
        return f"{speed // 1000}G"
    return f"{speed}M"


def _format_poe_state(device: Device, port: object) -> str:
    port_idx = _port_index(getattr(port, "port_idx", None), getattr(port, "name", None))
    if port_idx is not None and device.poe_ports.get(port_idx):
        return "active"
    if getattr(port, "port_poe", False) or getattr(port, "poe_enable", False):
        return "capable"
    return "-"


def _format_poe_power(power: float | None) -> str:
    if power is None or power <= 0:
        return "-"
    return f"{power:.2f}W"


def _port_index(port_idx: int | None, name: str | None) -> int | None:
    if port_idx is not None:
        return port_idx
    if name:
        return extract_port_number(name)
    return None


def _port_sort_key(port: object) -> tuple[int, str]:
    port_idx = _port_index(getattr(port, "port_idx", None), getattr(port, "name", None))
    if port_idx is not None:
        return (0, f"{port_idx:04d}")
    name = getattr(port, "name", "") or ""
    return (1, name.lower())


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _render_device_details(device: Device) -> list[str]:
    lines = [
        "#### Details",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Model | {_escape_cell(device.model_name or '-')} |",
        f"| IP | {_escape_cell(device.ip or '-')} |",
        f"| MAC | {_escape_cell(device.mac or '-')} |",
        f"| Firmware | {_escape_cell(device.version or '-')} |",
        f"| Uplink | {_escape_cell(_uplink_summary(device))} |",
        f"| Ports | {_escape_cell(_port_summary(device))} |",
        f"| PoE | {_escape_cell(_poe_summary(device))} |",
        "",
    ]
    return lines


def _port_summary(device: Device) -> str:
    ports = [port for port in device.port_table if port.port_idx is not None]
    if not ports:
        return "-"
    total_ports = len(ports)
    active_ports = sum(1 for port in ports if (port.speed or 0) > 0)
    return f"{total_ports} total, {active_ports} active"


def _poe_summary(device: Device) -> str:
    ports = [port for port in device.port_table if port.port_idx is not None]
    if not ports:
        return "-"
    poe_capable = sum(1 for port in ports if port.port_poe or port.poe_enable)
    poe_active = sum(1 for port in ports if device.poe_ports.get(port.port_idx or -1))
    total_power = sum(port.poe_power or 0.0 for port in ports)
    summary = f"{poe_capable} capable, {poe_active} active"
    if total_power > 0:
        summary = f"{summary}, {total_power:.2f}W"
    return summary


def _uplink_summary(device: Device) -> str:
    uplink = device.uplink or device.last_uplink
    if not uplink:
        return "-"
    name = uplink.name or uplink.mac or "Unknown"
    if uplink.port is not None:
        return f"{name} (Port {uplink.port})"
    return name
