"""Render LLDP data as Markdown tables."""

from __future__ import annotations

from collections.abc import Iterable

from ..model.helpers import normalize_mac
from ..model.lldp import LLDPEntry, local_port_label
from ..model.topology import (
    Device,
    _client_display_name,
    _client_matches_filters,
    _client_uplink_mac,
    _client_uplink_port,
    build_client_port_map,
    build_device_index,
    build_port_map,
)
from .device_ports_md import render_device_port_details
from .device_summary import poe_summary, port_summary, uplink_summary
from .markdown_tables import escape_markdown, markdown_table_lines
from .templating import render_template


def _lldp_sort_key(entry: LLDPEntry) -> tuple[int, str, str]:
    port_label = local_port_label(entry) or ""
    port_number = "".join(ch for ch in port_label if ch.isdigit())
    return (int(port_number or 0), port_label, entry.port_id)


def _client_summary(
    device: Device, client_rows: dict[str, list[tuple[str, str | None]]]
) -> tuple[str, str]:
    rows = client_rows.get(device.name)
    if rows is None:
        return "-", "-"
    count = len(rows)
    names = [name for name, _port in rows]
    sample = ", ".join(names[:3])
    if len(names) > 3:
        sample = f"{sample}, ..."
    return str(count), sample or "-"


def _details_table_lines(
    device: Device,
    client_rows: dict[str, list[tuple[str, str | None]]],
    client_mode: str,
) -> list[str]:
    wired_count, client_sample = _client_summary(device, client_rows)
    client_label = f"Clients ({client_mode})"
    rows = [
        ["Model", escape_markdown(device.model_name or device.type or "-")],
        ["Type", escape_markdown(device.type or "-")],
        ["IP", escape_markdown(device.ip or "-")],
        ["MAC", escape_markdown(device.mac or "-")],
        ["Firmware", escape_markdown(device.version or "-")],
        ["Uplink", escape_markdown(uplink_summary(device))],
        ["Ports", escape_markdown(port_summary(device))],
        ["PoE", escape_markdown(poe_summary(device))],
        [client_label, escape_markdown(wired_count)],
        ["Client examples", escape_markdown(client_sample)],
    ]
    lines = ["### Details", ""]
    lines.extend(markdown_table_lines(["Field", "Value"], rows))
    return lines


def _lldp_rows(
    entries: Iterable[LLDPEntry],
    device_index: dict[str, str],
) -> list[list[str]]:
    rows: list[list[str]] = []
    for entry in sorted(entries, key=_lldp_sort_key):
        local_label = local_port_label(entry) or "?"
        peer_name = device_index.get(normalize_mac(entry.chassis_id), "")
        peer_port = entry.port_id or "?"
        port_desc = entry.port_desc or ""
        rows.append(
            [
                local_label,
                peer_name or "-",
                peer_port,
                entry.chassis_id,
                port_desc or "-",
            ]
        )
    return rows


def _client_rows(
    clients: Iterable[object],
    device_index: dict[str, str],
    *,
    include_ports: bool,
    client_mode: str,
    only_unifi: bool,
) -> dict[str, list[tuple[str, str | None]]]:
    rows_by_device: dict[str, list[tuple[str, str | None]]] = {}
    for client in clients:
        if not _client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
            continue
        name = _client_display_name(client)
        uplink_mac = _client_uplink_mac(client)
        if not name or not uplink_mac:
            continue
        device_name = device_index.get(normalize_mac(uplink_mac))
        if not device_name:
            continue
        port_label = None
        if include_ports:
            uplink_port = _client_uplink_port(client)
            if uplink_port is not None:
                port_label = f"Port {uplink_port}"
        rows_by_device.setdefault(device_name, []).append((name, port_label))
    return rows_by_device


def _prepare_lldp_maps(
    devices: list[Device],
    *,
    clients: Iterable[object] | None,
    include_ports: bool,
    show_clients: bool,
    client_mode: str,
    only_unifi: bool,
) -> tuple[
    dict[tuple[str, str], str],
    dict[str, list[tuple[int, str]]] | None,
    dict[str, list[tuple[str, str | None]]],
]:
    device_index = build_device_index(devices)
    client_rows = (
        _client_rows(
            clients,
            device_index,
            include_ports=include_ports,
            client_mode=client_mode,
            only_unifi=only_unifi,
        )
        if clients
        else {}
    )
    port_map: dict[tuple[str, str], str] = {}
    client_port_map = None
    if include_ports:
        port_map = build_port_map(devices, only_unifi=False)
        if clients and show_clients:
            client_port_map = build_client_port_map(
                devices,
                clients,
                client_mode=client_mode,
                only_unifi=only_unifi,
            )
    return port_map, client_port_map, client_rows


def _render_device_lldp_section(
    device: Device,
    *,
    device_index: dict[str, str],
    port_map: dict[tuple[str, str], str],
    client_port_map: dict[str, list[tuple[int, str]]] | None,
    client_rows: dict[str, list[tuple[str, str | None]]],
    include_ports: bool,
    show_clients: bool,
    client_mode: str,
) -> str:
    details = "\n".join(_details_table_lines(device, client_rows, client_mode)).rstrip()
    ports_section = ""
    if include_ports:
        ports_section = "\n".join(
            [
                "### Ports",
                "",
                render_device_port_details(device, port_map, client_ports=client_port_map).strip(),
            ]
        ).rstrip()
    if device.lldp_info:
        lldp_section = "\n".join(
            markdown_table_lines(
                ["Local Port", "Neighbor", "Neighbor Port", "Chassis ID", "Port Description"],
                _lldp_rows(device.lldp_info, device_index),
                escape=escape_markdown,
            )
        ).rstrip()
    else:
        lldp_section = "_No LLDP neighbors._"
    clients_section = ""
    rows = client_rows.get(device.name)
    if rows and show_clients:
        if include_ports:
            clients_section = "\n".join(
                [
                    "### Clients",
                    "",
                    "\n".join(
                        markdown_table_lines(
                            ["Client", "Port"],
                            [
                                [escape_markdown(client_name), escape_markdown(port_label or "-")]
                                for client_name, port_label in rows
                            ],
                        )
                    ),
                ]
            ).rstrip()
        else:
            clients_section = "\n".join(
                ["### Clients", *[f"- {escape_markdown(name)}" for name, _ in rows]]
            ).rstrip()
    return render_template(
        "lldp_device_section.md.j2",
        device_name=device.name,
        details=details,
        ports_section=ports_section,
        lldp_section=lldp_section,
        clients_section=clients_section,
    ).rstrip()


def render_lldp_md(
    devices: list[Device],
    *,
    clients: Iterable[object] | None = None,
    include_ports: bool = False,
    show_clients: bool = False,
    client_mode: str = "wired",
    only_unifi: bool = False,
) -> str:
    device_index = build_device_index(devices)
    port_map, client_port_map, client_rows = _prepare_lldp_maps(
        devices,
        clients=clients,
        include_ports=include_ports,
        show_clients=show_clients,
        client_mode=client_mode,
        only_unifi=only_unifi,
    )
    sections: list[str] = []
    for device in sorted(devices, key=lambda item: item.name.lower()):
        sections.append(
            _render_device_lldp_section(
                device,
                device_index=device_index,
                port_map=port_map,
                client_port_map=client_port_map,
                client_rows=client_rows,
                include_ports=include_ports,
                show_clients=show_clients,
                client_mode=client_mode,
            )
        )
    body = "\n\n".join(section for section in sections if section).rstrip()
    return (
        render_template(
            "markdown_section.md.j2",
            title="LLDP Neighbors",
            body=body,
        ).rstrip()
        + "\n"
    )
