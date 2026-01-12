"""Home Assistant POC export helpers."""

from __future__ import annotations

import json
import logging
from html import escape as _escape_html
from pathlib import Path

from ..model.topology import Device, Edge, build_node_type_map
from ..render.svg import SvgOptions, render_svg
from ..render.svg_theme import SvgTheme
from .schema import HaSchema, build_ha_schema

logger = logging.getLogger(__name__)


def export_ha_assets(
    output_dir: str | Path,
    *,
    devices: list[Device],
    edges: list[Edge],
    clients: list[object] | None,
    svg_theme: SvgTheme,
    client_mode: str,
) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    node_types = build_node_type_map(devices, None, client_mode=client_mode)
    node_data = _build_node_data(devices)
    svg = render_svg(
        edges,
        node_types=node_types,
        node_data=node_data,
        options=SvgOptions(),
        theme=svg_theme,
    )
    schema = build_ha_schema(devices, edges, clients=clients, client_mode=client_mode)

    svg = _inject_svg_hooks(svg, schema)
    (target / "network.svg").write_text(svg, encoding="utf-8")
    (target / "network.json").write_text(_schema_json(schema), encoding="utf-8")
    (target / "lovelace.yaml").write_text(_lovelace_config(), encoding="utf-8")
    _write_card_stub(target)


def _schema_json(schema: HaSchema) -> str:
    payload = {
        "devices": schema.devices,
        "ports": schema.ports,
        "links": schema.links,
        "clients": schema.clients,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _lovelace_config() -> str:
    return (
        "type: custom:unifi-network-map\n"
        "svg_url: /local/unifi-network-maps/network.svg\n"
        "data_url: /local/unifi-network-maps/network.json\n"
    )


def _write_card_stub(target: Path) -> None:
    assets_dir = target
    assets_dir.mkdir(parents=True, exist_ok=True)
    stub_path = Path(__file__).parent / "assets" / "unifi-network-map.js"
    stub = stub_path.read_text(encoding="utf-8")
    (assets_dir / "unifi-network-map.js").write_text(stub, encoding="utf-8")


def _inject_svg_hooks(svg: str, schema: HaSchema) -> str:
    if "</svg>" not in svg:
        logger.warning("SVG output missing closing tag; skipping HA hooks")
        return svg
    hook_lines = ['<g id="ha-drilldown">']
    for device in schema.devices:
        device_id = _escape_html(str(device.get("id", "")))
        if device_id:
            hook_lines.append(
                f'<rect data-device-id="{device_id}" width="0" height="0" fill="none" />'
            )
    for port in schema.ports:
        port_id = _escape_html(str(port.get("id", "")))
        if port_id:
            hook_lines.append(f'<rect data-port-id="{port_id}" width="0" height="0" fill="none" />')
    hook_lines.append("</g>")
    hooks = "\n".join(hook_lines)
    return svg.replace("</svg>", f"{hooks}\n</svg>")


def _build_node_data(devices: list[Device]) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    for device in devices:
        device_id = device.mac or device.name
        if device_id:
            data[device.name] = {"data-device-id": device_id}
    return data
