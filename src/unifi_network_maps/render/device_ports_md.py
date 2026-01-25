"""Render per-device port overview tables."""

from __future__ import annotations

from collections import defaultdict
from html import escape as _escape_html

from ..model.ports import extract_port_number
from ..model.topology import ClientPortMap, Device, PortInfo, PortMap, classify_device_type
from .markdown_tables import markdown_table_lines
from .templating import render_template


def render_device_port_overview(
    devices: list[Device],
    port_map: PortMap,
    *,
    client_ports: ClientPortMap | None = None,
) -> str:
    gateways = _collect_devices_by_type(devices, "gateway")
    switches = _collect_devices_by_type(devices, "switch")
    sections: list[str] = []
    if gateways:
        sections.append(
            render_template(
                "markdown_section.md.j2",
                title="Gateways",
                body=_render_device_group(gateways, port_map, client_ports),
            ).rstrip()
        )
    if switches:
        sections.append(
            render_template(
                "markdown_section.md.j2",
                title="Switches",
                body=_render_device_group(switches, port_map, client_ports),
            ).rstrip()
        )
    return "\n\n".join(section for section in sections if section).rstrip() + "\n"


def _collect_devices_by_type(devices: list[Device], desired_type: str) -> list[Device]:
    return sorted(
        [device for device in devices if classify_device_type(device) == desired_type],
        key=lambda item: item.name.lower(),
    )


def _render_device_group(
    devices: list[Device],
    port_map: PortMap,
    client_ports: ClientPortMap | None,
) -> str:
    blocks: list[str] = []
    for device in devices:
        blocks.append(
            render_template(
                "device_port_block.md.j2",
                device_name=device.name,
                details="\n".join(_render_device_details(device)).rstrip(),
                ports="\n".join(_render_device_ports(device, port_map, client_ports)).rstrip(),
            ).rstrip()
        )
    return "\n\n".join(block for block in blocks if block)


def render_device_port_details(
    device: Device,
    port_map: PortMap,
    *,
    client_ports: ClientPortMap | None = None,
) -> str:
    lines = _render_device_details(device)
    lines.extend(_render_device_ports(device, port_map, client_ports))
    return "\n".join(lines).rstrip() + "\n"


def _render_device_ports(
    device: Device,
    port_map: PortMap,
    client_ports: ClientPortMap | None,
) -> list[str]:
    rows = _build_port_rows(device, port_map, client_ports)
    table_rows = [
        [
            _escape_markdown_text(port_label),
            _escape_connected_cell(connected or "-"),
            _escape_markdown_text(speed),
            _escape_markdown_text(poe_state),
            _escape_markdown_text(power),
        ]
        for port_label, connected, speed, poe_state, power in rows
    ]
    lines = ["#### Ports", ""]
    lines.extend(
        markdown_table_lines(
            ["Port", "Connected", "Speed", "PoE", "Power"],
            table_rows,
        )
    )
    return lines


def _build_port_rows(
    device: Device,
    port_map: PortMap,
    client_ports: ClientPortMap | None,
) -> list[tuple[str, str, str, str, str]]:
    connections = _device_port_connections(device.name, port_map)
    client_connections = _device_client_connections(device.name, client_ports)
    aggregated = _aggregate_ports(device.port_table)
    aggregated_indices = {
        port.port_idx
        for ports in aggregated.values()
        for port in ports
        if getattr(port, "port_idx", None) is not None
    }
    rows: list[tuple[tuple[int, int], tuple[str, str, str, str, str]]] = []
    seen_ports: set[int] = set()
    for port in sorted(device.port_table, key=_port_sort_key):
        if port.port_idx in aggregated_indices:
            port_idx = _port_index(port.port_idx, port.name)
            if port_idx is not None:
                seen_ports.add(port_idx)
            continue
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
                (0, port_idx or 10_000),
                (
                    port_label,
                    connected,
                    _format_speed(port.speed),
                    _format_poe_state(port),
                    _format_poe_power(port.poe_power),
                ),
            )
        )
    for _group_id, group_ports in aggregated.items():
        group_label = _format_aggregate_label(group_ports)
        group_sort = _aggregate_sort_key(group_ports)
        group_connections = _format_aggregate_connections(
            device.name,
            group_ports,
            connections,
            client_connections,
            port_map,
        )
        rows.append(
            (
                (0, group_sort),
                (
                    group_label,
                    group_connections,
                    _format_aggregate_speed(group_ports),
                    _format_aggregate_poe_state(group_ports),
                    _format_aggregate_power(group_ports),
                ),
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
        rows.append(((2, port_idx), (port_label, connected, "-", "-", "-")))
    return [row for _key, row in sorted(rows, key=lambda item: item[0])]


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
    peer_entries: list[str] = []
    for peer in sorted(peers, key=str.lower):
        peer_label = port_map.get((peer, device_name))
        if peer_label:
            peer_entries.append(
                f"{_escape_markdown_text(peer)} ({_escape_markdown_text(peer_label)})"
            )
        else:
            peer_entries.append(_escape_markdown_text(peer))
    peer_text = ", ".join(peer_entries)
    client_text = _format_client_connections(clients)
    if peer_text and client_text:
        return f"{peer_text}<br/>{client_text}"
    return peer_text or client_text


def _format_port_label(port_idx: int | None, name: str | None) -> str:
    if name and name.strip():
        normalized = name.strip()
        if port_idx is None:
            return normalized
        if normalized.lower() != f"port {port_idx}".lower():
            return normalized
    if port_idx is None:
        return "Port ?"
    return f"Port {port_idx}"


def _format_speed(speed: int | None) -> str:
    if speed is None or speed <= 0:
        return "-"
    if speed >= 1000:
        if speed % 1000 == 0:
            return f"{speed // 1000}G"
        return f"{speed / 1000:.1f}G"
    return f"{speed}M"


def _format_poe_state(port: object) -> str:
    poe_power = getattr(port, "poe_power", None)
    poe_good = getattr(port, "poe_good", False)
    poe_enable = getattr(port, "poe_enable", False)
    port_poe = getattr(port, "port_poe", False)
    if (poe_power or 0.0) > 0 or poe_good:
        return "active"
    if port_poe or poe_enable:
        if not poe_enable:
            return "disabled"
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


def _escape_markdown_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for char in ("|", "[", "]", "*", "_", "`", "<", ">"):
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def _escape_connected_cell(value: str) -> str:
    return value


def _render_device_details(device: Device) -> list[str]:
    lines = [
        "#### Details",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Model | {_escape_markdown_text(_device_model_label(device))} |",
        f"| Type | {_escape_markdown_text(device.type or '-')} |",
        f"| IP | {_escape_markdown_text(device.ip or '-')} |",
        f"| MAC | {_escape_markdown_text(device.mac or '-')} |",
        f"| Firmware | {_escape_markdown_text(device.version or '-')} |",
        f"| Uplink | {_escape_markdown_text(_uplink_summary(device))} |",
        f"| Ports | {_escape_markdown_text(_port_summary(device))} |",
        f"| PoE | {_escape_markdown_text(_poe_summary(device))} |",
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
    poe_active = sum(1 for port in ports if _format_poe_state(port) == "active")
    total_power = sum(port.poe_power or 0.0 for port in ports)
    summary = f"{poe_capable} capable, {poe_active} active"
    if total_power > 0:
        summary = f"{summary}, {total_power:.2f}W"
    return summary


def _uplink_summary(device: Device) -> str:
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


def _device_model_label(device: Device) -> str:
    if device.model_name:
        return device.model_name
    if device.model:
        return device.model
    return device.type or "-"


def _format_client_connections(clients: list[str]) -> str:
    if not clients:
        return ""
    if len(clients) == 1:
        return f"{_escape_markdown_text(clients[0])} (client)"
    items = "".join(f"<li>{_escape_html(name)}</li>" for name in clients)
    return f'<ul class="unifi-port-clients">{items}</ul>'


def _aggregate_base_groups(port_table: list[PortInfo]) -> dict[str, list[PortInfo]]:
    groups: dict[str, list[PortInfo]] = defaultdict(list)
    for port in port_table:
        group = getattr(port, "aggregation_group", None)
        if group:
            groups[str(group)].append(port)
            continue
        if _looks_like_lag(port):
            port_idx = getattr(port, "port_idx", None)
            if port_idx is not None:
                groups[f"lag-{port_idx}"].append(port)
    return groups


def _extend_singleton_groups(
    groups: dict[str, list[PortInfo]],
    port_table: list[PortInfo],
) -> None:
    if not groups:
        return
    port_by_idx: dict[int, PortInfo] = {
        port.port_idx: port for port in port_table if port.port_idx is not None
    }
    for group_id, group_ports in list(groups.items()):
        if len(group_ports) > 1:
            continue
        lone_port = group_ports[0]
        if not _looks_like_lag(lone_port):
            continue
        port_idx = lone_port.port_idx
        if port_idx is None:
            continue
        candidates: list[PortInfo] = []
        for neighbor in (port_idx - 1, port_idx + 1):
            port = port_by_idx.get(neighbor)
            if port and not getattr(port, "aggregation_group", None):
                if getattr(port, "speed", None) == getattr(lone_port, "speed", None):
                    candidates.append(port)
        if candidates:
            groups[group_id].extend(candidates)


def _aggregate_ports(port_table: list[PortInfo]) -> dict[str, list[PortInfo]]:
    groups = _aggregate_base_groups(port_table)
    _extend_singleton_groups(groups, port_table)
    return groups


def _looks_like_lag(port: PortInfo) -> bool:
    name = (getattr(port, "name", "") or "").lower()
    ifname = (getattr(port, "ifname", "") or "").lower()
    return "lag" in name or "lag" in ifname or "aggregate" in name


def _format_aggregate_label(group_ports: list[PortInfo]) -> str:
    ports = sorted([int(p.port_idx) for p in group_ports if p.port_idx is not None])
    if ports:
        if len(ports) == 1:
            return f"Port {ports[0]} (LAG)"
        if ports == list(range(ports[0], ports[-1] + 1)):
            return f"Port {ports[0]}-{ports[-1]} (LAG)"
        return "Ports " + "+".join(str(port) for port in ports) + " (LAG)"
    return "Aggregated ports"


def _aggregate_sort_key(group_ports: list[PortInfo]) -> int:
    ports = sorted([int(p.port_idx) for p in group_ports if p.port_idx is not None])
    return ports[0] if ports else 10_000


def _format_aggregate_connections(
    device_name: str,
    group_ports: list[PortInfo],
    connections: dict[int, list[str]],
    client_connections: dict[int, list[str]],
    port_map: PortMap,
) -> str:
    rendered: list[str] = []
    for port in group_ports:
        port_idx = _port_index(getattr(port, "port_idx", None), getattr(port, "name", None))
        if port_idx is None:
            continue
        text = _format_connections(
            device_name,
            port_idx,
            connections,
            client_connections,
            port_map,
        )
        if text:
            rendered.append(text)
    return ", ".join([item for item in rendered if item])


def _format_aggregate_speed(group_ports: list[PortInfo]) -> str:
    speeds = {getattr(port, "speed", None) for port in group_ports}
    speeds.discard(None)
    if not speeds:
        return "-"
    if len(speeds) == 1:
        return _format_speed(next(iter(speeds)))
    return "mixed"


def _format_aggregate_poe_state(group_ports: list[PortInfo]) -> str:
    states = {_format_poe_state(port) for port in group_ports}
    if "active" in states:
        return "active"
    if "disabled" in states:
        return "disabled"
    if "capable" in states:
        return "capable"
    return "-"


def _format_aggregate_power(group_ports: list[PortInfo]) -> str:
    total = sum(getattr(port, "poe_power", 0.0) or 0.0 for port in group_ports)
    return _format_poe_power(total)
