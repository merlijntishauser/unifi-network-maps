"""Device inventory table rendering."""

from __future__ import annotations

from ..model.inventory import DeviceInfo


def render_device_inventory_table(
    inventory: list[DeviceInfo],
    *,
    include_hostname: bool = True,
) -> str:
    """Render a markdown table of infrastructure devices.

    When include_hostname is False, the Hostname column is omitted.
    """
    if not inventory:
        return ""

    if include_hostname:
        header = "| Name | Type | Model | IP | Hostname | MAC | Firmware |"
        separator = "|------|------|-------|----|----------|-----|----------|"
        rows = [
            f"| {d.name} | {d.device_type} | {d.model_name} | {d.ip}"
            f" | {d.hostname or ''} | {d.mac} | {d.firmware} |"
            for d in inventory
        ]
    else:
        header = "| Name | Type | Model | IP | MAC | Firmware |"
        separator = "|------|------|-------|----|-----|----------|"
        rows = [
            f"| {d.name} | {d.device_type} | {d.model_name} | {d.ip} | {d.mac} | {d.firmware} |"
            for d in inventory
        ]

    return "\n".join([header, separator, *rows]) + "\n"
