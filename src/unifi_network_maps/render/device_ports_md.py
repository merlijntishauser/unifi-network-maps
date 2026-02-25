"""Render per-device port overview tables."""

from __future__ import annotations

from collections import defaultdict
from html import escape as _escape_html

from unifi_topology.model.classify import classify_device_type
from unifi_topology.model.ports import extract_port_number
from unifi_topology.model.topology import ClientPortMap, Device, PortInfo, PortMap

from .device_ports_aggregate import (
    aggregate_ports,
    aggregate_sort_key,
    format_aggregate_label,
    port_index,
)
from .device_summary import poe_summary, port_summary, uplink_summary
from .markdown_tables import escape_markdown, markdown_table_lines
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
            escape_markdown(port_label),
            connected or "-",  # Not escaped: contains intentional HTML (br, ul)
            escape_markdown(speed),
            escape_markdown(poe_state),
            escape_markdown(power),
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


_SortedRow = tuple[tuple[int, int], tuple[str, str, str, str, str]]


def _build_individual_port_rows(
    device: Device,
    aggregated_indices: set[int],
    connections: dict[int, list[str]],
    client_connections: dict[int, list[str]],
    port_map: PortMap,
) -> tuple[list[_SortedRow], set[int]]:
    rows: list[_SortedRow] = []
    seen_ports: set[int] = set()
    for port in sorted(device.port_table, key=_port_sort_key):
        idx = port_index(port.port_idx, port.name)
        if port.port_idx in aggregated_indices:
            if idx is not None:
                seen_ports.add(idx)
            continue
        if idx is not None:
            seen_ports.add(idx)
        port_label = _format_port_label(idx, port.name)
        connected = _format_connections(
            device.name,
            idx,
            connections,
            client_connections,
            port_map,
        )
        rows.append(
            (
                (0, idx or 10_000),
                (
                    port_label,
                    connected,
                    _format_speed(port.speed),
                    _format_poe_state(port),
                    _format_poe_power(port.poe_power),
                ),
            )
        )
    return rows, seen_ports


def _build_aggregate_rows(
    device_name: str,
    aggregated: dict[str, list[PortInfo]],
    connections: dict[int, list[str]],
    client_connections: dict[int, list[str]],
    port_map: PortMap,
) -> list[_SortedRow]:
    rows: list[_SortedRow] = []
    for _group_id, group_ports in aggregated.items():
        group_connections = _format_aggregate_connections(
            device_name,
            group_ports,
            connections,
            client_connections,
            port_map,
        )
        rows.append(
            (
                (0, aggregate_sort_key(group_ports)),
                (
                    format_aggregate_label(group_ports),
                    group_connections,
                    _format_aggregate_speed(group_ports),
                    _format_aggregate_poe_state(group_ports),
                    _format_aggregate_power(group_ports),
                ),
            )
        )
    return rows


def _build_orphan_connection_rows(
    device_name: str,
    connections: dict[int, list[str]],
    client_connections: dict[int, list[str]],
    seen_ports: set[int],
    port_map: PortMap,
) -> list[_SortedRow]:
    rows: list[_SortedRow] = []
    for pidx in sorted(connections):
        if pidx in seen_ports:
            continue
        port_label = _format_port_label(pidx, None)
        connected = _format_connections(
            device_name,
            pidx,
            connections,
            client_connections,
            port_map,
        )
        rows.append(((2, pidx), (port_label, connected, "-", "-", "-")))
    return rows


def _build_port_rows(
    device: Device,
    port_map: PortMap,
    client_ports: ClientPortMap | None,
) -> list[tuple[str, str, str, str, str]]:
    connections = _device_port_connections(device.name, port_map)
    client_connections = _device_client_connections(device.name, client_ports)
    aggregated = aggregate_ports(device.port_table)
    aggregated_indices = {
        port.port_idx
        for ports in aggregated.values()
        for port in ports
        if port.port_idx is not None
    }
    rows: list[_SortedRow] = []
    individual, seen_ports = _build_individual_port_rows(
        device,
        aggregated_indices,
        connections,
        client_connections,
        port_map,
    )
    rows.extend(individual)
    rows.extend(
        _build_aggregate_rows(
            device.name,
            aggregated,
            connections,
            client_connections,
            port_map,
        )
    )
    rows.extend(
        _build_orphan_connection_rows(
            device.name,
            connections,
            client_connections,
            seen_ports,
            port_map,
        )
    )
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
            peer_entries.append(f"{escape_markdown(peer)} ({escape_markdown(peer_label)})")
        else:
            peer_entries.append(escape_markdown(peer))
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


def _format_poe_state(port: PortInfo) -> str:
    if (port.poe_power or 0.0) > 0 or port.poe_good:
        return "active"
    if port.port_poe or port.poe_enable:
        if not port.poe_enable:
            return "disabled"
        return "capable"
    return "-"


def _format_poe_power(power: float | None) -> str:
    if power is None or power <= 0:
        return "-"
    return f"{power:.2f}W"


def _port_sort_key(port: PortInfo) -> tuple[int, str]:
    idx = port_index(port.port_idx, port.name)
    if idx is not None:
        return (0, f"{idx:04d}")
    return (1, (port.name or "").lower())


def _render_device_details(device: Device) -> list[str]:
    lines = [
        "#### Details",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Model | {escape_markdown(_device_model_label(device))} |",
        f"| Type | {escape_markdown(device.type or '-')} |",
        f"| IP | {escape_markdown(device.ip or '-')} |",
        f"| MAC | {escape_markdown(device.mac or '-')} |",
        f"| Firmware | {escape_markdown(device.version or '-')} |",
        f"| Uplink | {escape_markdown(uplink_summary(device))} |",
        f"| Ports | {escape_markdown(port_summary(device))} |",
        f"| PoE | {escape_markdown(poe_summary(device))} |",
        "",
    ]
    return lines


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
        return f"{escape_markdown(clients[0])} (client)"
    items = "".join(f"<li>{_escape_html(name)}</li>" for name in clients)
    return f'<ul class="unifi-port-clients">{items}</ul>'


def _format_aggregate_connections(
    device_name: str,
    group_ports: list[PortInfo],
    connections: dict[int, list[str]],
    client_connections: dict[int, list[str]],
    port_map: PortMap,
) -> str:
    rendered: list[str] = []
    for port in group_ports:
        port_idx = port_index(port.port_idx, port.name)
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
    speeds = {port.speed for port in group_ports}
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
    total = sum(port.poe_power or 0.0 for port in group_ports)
    return _format_poe_power(total)
