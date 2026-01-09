"""Debug helpers for dumping device data."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Sequence

from ..model.topology import Device, group_devices_by_type

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


def debug_dump_devices(
    raw_devices: Sequence[object],
    normalized: Iterable[Device],
    *,
    sample_count: int,
) -> None:
    name_to_device: dict[str, object] = {}
    for device in raw_devices:
        name = getattr(device, "name", None)
        if name:
            name_to_device[name] = device

    groups = group_devices_by_type(normalized)
    gateways = groups.get("gateway", [])
    samples: list[str] = []
    for group in ("switch", "ap", "other"):
        for name in groups.get(group, []):
            if name not in gateways:
                samples.append(name)
            if len(samples) >= sample_count:
                break
        if len(samples) >= sample_count:
            break

    selected_names = gateways[:1] + samples
    payload = []
    for name in selected_names:
        device = name_to_device.get(name)
        if device is None:
            continue
        payload.append({"name": name, "data": device_to_dict(device)})

    logger.info("Debug dump devices: %s", json.dumps(payload, indent=2, sort_keys=True))
