"""Debug helpers for dumping device data."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence

from unifi_topology.model.edges import group_devices_by_type
from unifi_topology.model.topology import Device

logger = logging.getLogger(__name__)


def device_to_dict(device: object) -> dict[str, object]:
    to_dict = getattr(device, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, dict):
            return result
        return {"repr": repr(result)}
    if hasattr(device, "__dict__"):
        return dict(device.__dict__)
    if isinstance(device, dict):
        return dict(device)
    return {"repr": repr(device)}


def _sample_non_gateway_macs(
    groups: dict[str, list[str]],
    gateways: list[str],
    sample_count: int,
) -> list[str]:
    """Pick up to *sample_count* device MACs from non-gateway groups."""
    samples: list[str] = []
    for group in ("switch", "ap", "other"):
        for mac in groups.get(group, []):
            if mac not in gateways:
                samples.append(mac)
            if len(samples) >= sample_count:
                return samples
    return samples


def debug_dump_devices(
    raw_devices: Sequence[object],
    normalized: Iterable[Device],
    *,
    sample_count: int,
) -> None:
    mac_to_device: dict[str, object] = {}
    mac_to_name: dict[str, str] = {}
    for device in raw_devices:
        mac = getattr(device, "mac", None)
        name = getattr(device, "name", None)
        if mac:
            mac_to_device[mac] = device
            if name:
                mac_to_name[mac] = name

    groups = group_devices_by_type(normalized)
    gateways = groups.get("gateway", [])
    samples = _sample_non_gateway_macs(groups, gateways, sample_count)

    selected = gateways[:1] + samples
    payload = []
    for mac in selected:
        device = mac_to_device.get(mac)
        if device is None:
            continue
        name = mac_to_name.get(mac, mac)
        payload.append({"name": name, "data": device_to_dict(device)})

    logger.info("Debug dump devices: %s", json.dumps(payload, indent=2, sort_keys=True))
