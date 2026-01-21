from __future__ import annotations

from unifi_network_maps.model.topology import Device
from unifi_network_maps.render import mkdocs
from unifi_network_maps.render.mermaid_theme import DEFAULT_THEME


def _device(name: str = "Switch A") -> Device:
    return Device(name=name, model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[])


def _options(*, legend_style: str, dual_theme: bool) -> mkdocs.MkdocsRenderOptions:
    return mkdocs.MkdocsRenderOptions(
        direction="TB",
        legend_style=legend_style,
        legend_scale=1.0,
        timestamp_zone="off",
        client_scope="wired",
        dual_theme=dual_theme,
    )


def test_timestamp_line_off_returns_empty():
    assert mkdocs._timestamp_line("off") == ""


def test_timestamp_line_invalid_zone_warns(caplog):
    with caplog.at_level("WARNING"):
        assert mkdocs._timestamp_line("Nowhere/Invalid") == ""
    assert "Invalid mkdocs timestamp zone" in caplog.text


def test_mkdocs_single_legend_block_compact():
    content = mkdocs._mkdocs_single_legend_block(
        "compact",
        mermaid_theme=DEFAULT_THEME,
        legend_scale=1.0,
    )
    assert "data-unifi-legend" in content
    assert "unifi-legend" in content


def test_mkdocs_single_legend_block_mermaid():
    content = mkdocs._mkdocs_single_legend_block(
        "diagram",
        mermaid_theme=DEFAULT_THEME,
        legend_scale=1.0,
    )
    assert content.startswith("```mermaid\n")
    assert content.endswith("```")


def test_mkdocs_dual_legend_block_compact():
    content = mkdocs._mkdocs_dual_legend_block(
        "compact",
        mermaid_theme=DEFAULT_THEME,
        dark_mermaid_theme=DEFAULT_THEME,
        legend_scale=1.0,
    )
    assert "unifi-legend--light" in content
    assert "unifi-legend--dark" in content


def test_mkdocs_dual_legend_block_mermaid():
    content = mkdocs._mkdocs_dual_legend_block(
        "diagram",
        mermaid_theme=DEFAULT_THEME,
        dark_mermaid_theme=DEFAULT_THEME,
        legend_scale=1.0,
    )
    assert "unifi-legend--light" in content
    assert "unifi-legend--dark" in content
    assert "```mermaid" in content


def test_mkdocs_dual_mermaid_block_wraps_light_and_dark():
    content = mkdocs._mkdocs_dual_mermaid_block("graph TB", "graph TB", base_class="unifi-mermaid")
    assert "unifi-mermaid--light" in content
    assert "unifi-mermaid--dark" in content


def test_mkdocs_dual_theme_style_renders():
    content = mkdocs._mkdocs_dual_theme_style()
    assert "unifi-mermaid" in content


def test_render_mkdocs_single_theme_compact_legend():
    output = mkdocs.render_mkdocs(
        edges=[],
        devices=[_device()],
        mermaid_theme=DEFAULT_THEME,
        port_map={},
        client_ports=None,
        options=_options(legend_style="compact", dual_theme=False),
    )
    assert "## Map" in output
    assert "## Legend" not in output
    assert "data-unifi-legend" in output


def test_render_mkdocs_dual_theme_mermaid_legend():
    output = mkdocs.render_mkdocs(
        edges=[],
        devices=[_device()],
        mermaid_theme=DEFAULT_THEME,
        port_map={},
        client_ports=None,
        options=_options(legend_style="diagram", dual_theme=True),
        dark_mermaid_theme=DEFAULT_THEME,
    )
    assert "## Legend" in output
    assert "unifi-mermaid--light" in output
    assert "unifi-mermaid--dark" in output
