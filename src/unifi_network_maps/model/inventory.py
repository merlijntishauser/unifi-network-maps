"""Device inventory model."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Sequence
from dataclasses import dataclass

from .classify import classify_client_type, classify_device_type, client_display_name
from .clients import client_matches_filters
from .helpers import first_string_field, get_field
from .topology import Device


@dataclass(frozen=True)
class DeviceInfo:
    """Structured inventory entry for a network infrastructure device."""

    name: str
    device_type: str
    model_name: str
    ip: str
    hostname: str | None
    mac: str
    firmware: str


def _ip_sort_key(ip: str) -> tuple[int, ...]:
    """Return a tuple for numeric IP sorting."""
    try:
        return tuple(ipaddress.ip_address(ip).packed)
    except ValueError:
        return (255, 255, 255, 255)


def build_device_inventory(
    devices: list[Device],
    hostnames: dict[str, str] | None = None,
) -> list[DeviceInfo]:
    """Convert devices to a sorted inventory list.

    Joins hostname from the hostnames map (keyed by IP).
    Sorted by IP address.
    """
    inventory: list[DeviceInfo] = []
    for device in devices:
        device_type = classify_device_type(device)
        hostname = hostnames.get(device.ip) if hostnames else None
        inventory.append(
            DeviceInfo(
                name=device.name,
                device_type=device_type,
                model_name=device.model_name,
                ip=device.ip,
                hostname=hostname,
                mac=device.mac,
                firmware=device.version,
            )
        )
    inventory.sort(key=lambda d: _ip_sort_key(d.ip))
    return inventory


def _client_model(client: object) -> str:
    """Extract model name from client UniFi device info."""
    ucore = get_field(client, "unifi_device_info_from_ucore")
    if isinstance(ucore, dict):
        model = first_string_field(ucore, "computed_model", "product_model", "product_shortname")
        if model:
            return model
    return ""


_FW_VERSION_RE = re.compile(r"v(\d+\.\d+\.\d+(?:\.\d+)?)")


def _extract_fw_version(raw: str) -> str:
    """Extract a clean version number from a UniFi firmware build string.

    Matches 3- or 4-segment version after a 'v' prefix.
    Example: "UVC.SAV539g.v5.2.52.67.39be8f1.260203.0900" -> "5.2.52.67"
    """
    match = _FW_VERSION_RE.search(raw)
    return match.group(1) if match else raw


def _client_firmware(client: object) -> str:
    """Extract firmware version from client data."""
    ucore = get_field(client, "unifi_device_info_from_ucore")
    if isinstance(ucore, dict):
        fw = first_string_field(ucore, "fw_version")
        if fw:
            return _extract_fw_version(fw)
    fw = first_string_field(client, "fw_version")
    if fw:
        return _extract_fw_version(fw)
    return ""


def build_client_inventory(
    clients: Sequence[object],
    hostnames: dict[str, str] | None = None,
    *,
    client_mode: str = "all",
    only_unifi: bool = False,
) -> list[DeviceInfo]:
    """Convert clients to a sorted inventory list.

    Applies client_mode and only_unifi filters.
    Joins hostname from the hostnames map (keyed by IP).
    Sorted by IP address.
    """
    inventory: list[DeviceInfo] = []
    for client in clients:
        if not client_matches_filters(client, client_mode=client_mode, only_unifi=only_unifi):
            continue
        name = client_display_name(client) or ""
        if not name:
            continue
        ip = get_field(client, "ip")
        ip_str = ip if isinstance(ip, str) else ""
        mac = get_field(client, "mac")
        mac_str = mac if isinstance(mac, str) else ""
        hostname = hostnames.get(ip_str) if hostnames and ip_str else None
        inventory.append(
            DeviceInfo(
                name=name,
                device_type=classify_client_type(client),
                model_name=_client_model(client),
                ip=ip_str,
                hostname=hostname,
                mac=mac_str,
                firmware=_client_firmware(client),
            )
        )
    inventory.sort(key=lambda d: _ip_sort_key(d.ip))
    return inventory
