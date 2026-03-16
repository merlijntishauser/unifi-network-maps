"""Rendering backends for network diagrams."""

from unifi_topology.render import (
    DEFAULT_MERMAID_THEME,
    MermaidTheme,
    render_device_inventory_table,
    render_device_port_overview,
    render_dual,
    render_legend,
    render_legend_compact,
    render_lldp_md,
    render_mermaid,
    render_svg,
    render_svg_isometric,
)
from unifi_topology.render.svg_theme import DEFAULT_THEME as DEFAULT_SVG_THEME
from unifi_topology.render.svg_theme import SvgOptions, SvgTheme

from .theme import resolve_themes

__all__ = [
    "DEFAULT_MERMAID_THEME",
    "DEFAULT_SVG_THEME",
    "MermaidTheme",
    "SvgOptions",
    "SvgTheme",
    "render_device_inventory_table",
    "render_device_port_overview",
    "render_dual",
    "render_legend",
    "render_legend_compact",
    "render_lldp_md",
    "render_mermaid",
    "render_svg",
    "render_svg_isometric",
    "resolve_themes",
]
