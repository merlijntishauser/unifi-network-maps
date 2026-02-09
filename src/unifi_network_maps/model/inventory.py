"""Device inventory model."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from .classify import classify_device_type
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
