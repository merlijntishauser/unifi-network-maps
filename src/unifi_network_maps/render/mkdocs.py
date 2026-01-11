"""MkDocs-specific rendering helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from ..model.topology import ClientPortMap, Device, PortMap, build_node_type_map
from .device_ports_md import render_device_port_overview
from .mermaid import render_legend, render_legend_compact, render_mermaid
from .mermaid_theme import MermaidTheme
from .templating import render_template

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MkdocsRenderOptions:
    direction: str
    legend_style: str
    legend_scale: float
    timestamp_zone: str
    client_scope: str
    dual_theme: bool


def render_mkdocs(
    edges: list,
    devices: list[Device],
    *,
    mermaid_theme: MermaidTheme,
    port_map: PortMap,
    client_ports: ClientPortMap | None,
    options: MkdocsRenderOptions,
    dark_mermaid_theme: MermaidTheme | None = None,
) -> str:
    clients = None
    node_types = build_node_type_map(devices, clients, client_mode=options.client_scope)
    content = render_mermaid(
        edges,
        direction=options.direction,
        node_types=node_types,
        theme=mermaid_theme,
    )
    dual_theme = options.dual_theme and dark_mermaid_theme is not None
    legend_title = "Legend" if options.legend_style != "compact" else ""
    if dual_theme and dark_mermaid_theme is not None:
        dark_content = render_mermaid(
            edges,
            direction=options.direction,
            node_types=node_types,
            theme=dark_mermaid_theme,
        )
        map_block = _mkdocs_dual_mermaid_block(content, dark_content, base_class="unifi-mermaid")
        legend_block = _mkdocs_dual_legend_block(
            options.legend_style,
            mermaid_theme=mermaid_theme,
            dark_mermaid_theme=dark_mermaid_theme,
            legend_scale=options.legend_scale,
        )
        dual_style = _mkdocs_dual_theme_style()
    else:
        map_block = _mkdocs_mermaid_block(content, class_name="unifi-mermaid")
        legend_block = _mkdocs_single_legend_block(
            options.legend_style,
            mermaid_theme=mermaid_theme,
            legend_scale=options.legend_scale,
        )
        dual_style = ""
    return render_template(
        "mkdocs_document.md.j2",
        title="UniFi network",
        timestamp_line=_timestamp_line(options.timestamp_zone),
        dual_style=dual_style,
        map_block=map_block,
        legend_title=legend_title,
        legend_block=legend_block,
        device_overview=render_device_port_overview(
            devices, port_map, client_ports=client_ports
        ).rstrip()
        + "\n",
    )


def _timestamp_line(timestamp_zone: str) -> str:
    if timestamp_zone.strip().lower() in {"off", "none", "false"}:
        return ""
    try:
        zone = ZoneInfo(timestamp_zone)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Invalid mkdocs timestamp zone '%s': %s", timestamp_zone, exc)
        return ""
    generated_at = datetime.now(zone).strftime("%Y-%m-%d %H:%M:%S %Z")
    return f"Generated: {generated_at}"


def _mkdocs_mermaid_block(content: str, *, class_name: str) -> str:
    return render_template(
        "mkdocs_mermaid_block.md.j2",
        class_name=class_name,
        content=content,
    )


def _mkdocs_dual_mermaid_block(
    light_content: str,
    dark_content: str,
    *,
    base_class: str,
) -> str:
    light = _mkdocs_mermaid_block(light_content, class_name=f"{base_class} {base_class}--light")
    dark = _mkdocs_mermaid_block(dark_content, class_name=f"{base_class} {base_class}--dark")
    return f"{light}\n{dark}"


def _mkdocs_single_legend_block(
    legend_style: str,
    *,
    mermaid_theme: MermaidTheme,
    legend_scale: float,
) -> str:
    if legend_style == "compact":
        return render_template(
            "mkdocs_html_block.html.j2",
            class_name="unifi-legend",
            data_unifi_legend=True,
            content=render_legend_compact(theme=mermaid_theme),
        )
    return "```mermaid\n" + render_legend(theme=mermaid_theme, legend_scale=legend_scale) + "```"


def _mkdocs_dual_legend_block(
    legend_style: str,
    *,
    mermaid_theme: MermaidTheme,
    dark_mermaid_theme: MermaidTheme,
    legend_scale: float,
) -> str:
    if legend_style == "compact":
        light = render_template(
            "mkdocs_html_block.html.j2",
            class_name="unifi-legend unifi-legend--light",
            data_unifi_legend=True,
            content=render_legend_compact(theme=mermaid_theme),
        )
        dark = render_template(
            "mkdocs_html_block.html.j2",
            class_name="unifi-legend unifi-legend--dark",
            data_unifi_legend=True,
            content=render_legend_compact(theme=dark_mermaid_theme),
        )
        return f"{light}\n{dark}"
    light = _mkdocs_mermaid_block(
        render_legend(theme=mermaid_theme, legend_scale=legend_scale),
        class_name="unifi-legend unifi-legend--light",
    )
    dark = _mkdocs_mermaid_block(
        render_legend(theme=dark_mermaid_theme, legend_scale=legend_scale),
        class_name="unifi-legend unifi-legend--dark",
    )
    return f"{light}\n{dark}"


def _mkdocs_dual_theme_style() -> str:
    return render_template("mkdocs_dual_theme_style.html.j2") + "\n"
