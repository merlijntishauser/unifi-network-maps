"""Render LLDP data as Markdown tables."""

from __future__ import annotations

from collections.abc import Iterable

from ..model.lldp import LLDPEntry, local_port_label
from ..model.ports import extract_port_number
from ..model.topology import Device, build_client_port_map, build_device_index, build_port_map
from .device_ports_md import render_device_port_details
from .markdown_tables import markdown_table_lines
from .templating import render_template


def _normalize_mac(value: str) -> str:
    return value.strip().lower()


def _client_field(client: object, name: str) -> object | None:
    if isinstance(client, dict):
        return client.get(name)
    return getattr(client, name, None)


def _client_display_name(client: object) -> str | None:
    raw_name = _client_field(client, "name")
    if isinstance(raw_name, str) and raw_name.strip():
        return raw_name.strip()
    preferred = _client_ucore_display_name(client)
    if preferred:
        return preferred
    for key in ("hostname", "mac"):
        value = _client_field(client, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _client_uplink_mac(client: object) -> str | None:
    for key in ("ap_mac", "sw_mac", "uplink_mac", "uplink_device_mac", "last_uplink_mac"):
        value = _client_field(client, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("uplink", "last_uplink"):
        nested = _client_field(client, key)
        if isinstance(nested, dict):
            value = nested.get("uplink_mac") or nested.get("uplink_device_mac")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _client_uplink_port(client: object) -> int | None:
    for value in _client_port_values(client):
        parsed = _parse_port_value(value)
        if parsed is not None:
            return parsed
    return None


def _client_port_values(client: object) -> Iterable[object | None]:
    for key in ("uplink_remote_port", "sw_port", "ap_port", "port_idx"):
        yield _client_field(client, key)
    for key in ("uplink", "last_uplink"):
        nested = _client_field(client, key)
        if isinstance(nested, dict):
            for nested_key in ("uplink_remote_port", "port_idx"):
                yield nested.get(nested_key)


def _parse_port_value(value: object | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return extract_port_number(stripped)
    return None


def _client_is_wired(client: object) -> bool:
    return bool(_client_field(client, "is_wired"))


def _client_unifi_flag(client: object) -> bool | None:
    for key in ("is_unifi", "is_unifi_device", "is_ubnt", "is_uap", "is_managed"):
        value = _client_field(client, key)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
    return None


def _client_vendor(client: object) -> str | None:
    for key in ("oui", "vendor", "vendor_name", "manufacturer", "manufacturer_name"):
        value = _client_field(client, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _client_ucore_info(client: object) -> dict[str, object] | None:
    info = _client_field(client, "unifi_device_info_from_ucore")
    if isinstance(info, dict):
        return info
    return None


def _client_ucore_display_name(client: object) -> str | None:
    ucore = _client_ucore_info(client)
    if not ucore:
        return None
    for key in ("name", "computed_model", "product_model", "product_shortname"):
        value = ucore.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _client_hostname_source(client: object) -> str | None:
    value = _client_field(client, "hostname_source")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _client_is_unifi(client: object) -> bool:
    flag = _client_unifi_flag(client)
    if flag is not None:
        return flag
    ucore = _client_ucore_info(client)
    if ucore:
        managed = ucore.get("managed")
        if isinstance(managed, bool) and managed:
            return True
        if isinstance(ucore.get("product_line"), str) and ucore.get("product_line"):
            return True
        if isinstance(ucore.get("product_shortname"), str) and ucore.get("product_shortname"):
            return True
        for key in ("name", "computed_model", "product_model"):
            value = ucore.get(key)
            if isinstance(value, str) and value.strip():
                return True
    vendor = _client_vendor(client)
    if not vendor:
        return False
    normalized = vendor.lower()
    return "ubiquiti" in normalized or "unifi" in normalized


def _client_matches_mode(client: object, mode: str) -> bool:
    wired = _client_is_wired(client)
    if mode == "all":
        return True
    if mode == "wireless":
        return not wired
    return wired


def _client_matches_filters(client: object, *, client_mode: str, only_unifi: bool) -> bool:
    if not _client_matches_mode(client, client_mode):
        return False
    if only_unifi and not _client_is_unifi(client):
        return False
    return True


def _lldp_sort_key(entry: LLDPEntry) -> tuple[int, str, str]:
    port_label = local_port_label(entry) or ""
    port_number = "".join(ch for ch in port_label if ch.isdigit())
    return (int(port_number or 0), port_label, entry.port_id)


def _port_summary(device: Device) -> str:
    ports = [port for port in device.port_table if port.port_idx is not None]
    if not ports:
        return "-"
    total_ports = len(ports)
    poe_capable = sum(1 for port in ports if port.port_poe or port.poe_enable)
    poe_active = sum(1 for port in ports if device.poe_ports.get(port.port_idx or -1))
    total_power = sum(port.poe_power or 0.0 for port in ports)
    summary = f"Total {total_ports}, PoE {poe_capable} (active {poe_active})"
    if total_power > 0:
        summary = f"{summary}, {total_power:.2f}W"
    return summary


def _poe_summary(device: Device) -> str:
    ports = [port for port in device.port_table if port.port_idx is not None]
    if not ports:
        return "-"
    poe_capable = sum(1 for port in ports if port.port_poe or port.poe_enable)
    poe_active = sum(1 for port in ports if (port.poe_power or 0.0) > 0 or port.poe_good)
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
        ["Model", _escape_cell(device.model_name or device.type or "-")],
        ["Type", _escape_cell(device.type or "-")],
        ["IP", _escape_cell(device.ip or "-")],
        ["MAC", _escape_cell(device.mac or "-")],
        ["Firmware", _escape_cell(device.version or "-")],
        ["Uplink", _escape_cell(_uplink_summary(device))],
        ["Ports", _escape_cell(_port_summary(device))],
        ["PoE", _escape_cell(_poe_summary(device))],
        [client_label, _escape_cell(wired_count)],
        ["Client examples", _escape_cell(client_sample)],
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
        peer_name = device_index.get(_normalize_mac(entry.chassis_id), "")
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


def _escape_cell(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    for char in ("|", "[", "]", "*", "_", "`", "<", ">"):
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


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
        device_name = device_index.get(_normalize_mac(uplink_mac))
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
                escape=_escape_cell,
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
                                [_escape_cell(client_name), _escape_cell(port_label or "-")]
                                for client_name, port_label in rows
                            ],
                        )
                    ),
                ]
            ).rstrip()
        else:
            clients_section = "\n".join(
                ["### Clients", *[f"- {_escape_cell(name)}" for name, _ in rows]]
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
