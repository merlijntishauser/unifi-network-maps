from __future__ import annotations

from importlib import import_module


def test_legacy_render_modules_remain_importable():
    expected = {
        "unifi_network_maps.render.device_ports_aggregate": [
            "aggregate_ports",
            "format_aggregate_label",
        ],
        "unifi_network_maps.render.device_ports_md": [
            "render_device_port_details",
            "render_device_port_overview",
        ],
        "unifi_network_maps.render.device_summary": [
            "poe_summary",
            "port_summary",
            "uplink_summary",
        ],
        "unifi_network_maps.render.lldp_md": ["render_lldp_md", "_client_rows"],
        "unifi_network_maps.render.markdown_tables": [
            "escape_markdown",
            "markdown_table_lines",
        ],
        "unifi_network_maps.render.mermaid": [
            "render_legend",
            "render_legend_compact",
            "render_mermaid",
        ],
        "unifi_network_maps.render.mermaid_theme": [
            "DEFAULT_THEME",
            "MermaidTheme",
            "class_defs",
        ],
    }
    for module_name, attrs in expected.items():
        module = import_module(module_name)
        for attr in attrs:
            assert hasattr(module, attr), f"{module_name} missing {attr}"
