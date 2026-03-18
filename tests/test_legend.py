"""Tests for legend rendering helpers."""

from __future__ import annotations

from unifi_topology.render.mermaid_theme import DEFAULT_THEME

from unifi_network_maps.render.legend import render_legend_only, resolve_legend_style

# --- resolve_legend_style ---


class TestResolveLegendStyle:
    def test_auto_mkdocs_returns_compact(self):
        assert resolve_legend_style(format_name="mkdocs", legend_style="auto") == "compact"

    def test_auto_svg_returns_diagram(self):
        assert resolve_legend_style(format_name="svg", legend_style="auto") == "diagram"

    def test_auto_mermaid_returns_diagram(self):
        assert resolve_legend_style(format_name="mermaid", legend_style="auto") == "diagram"

    def test_explicit_compact_preserved(self):
        assert resolve_legend_style(format_name="svg", legend_style="compact") == "compact"

    def test_explicit_diagram_preserved(self):
        assert resolve_legend_style(format_name="mkdocs", legend_style="diagram") == "diagram"


# --- render_legend_only ---


class TestRenderLegendOnly:
    def test_compact_style_returns_markdown_table(self):
        result = render_legend_only(
            legend_style="compact",
            legend_scale=1.0,
            markdown=False,
            theme=DEFAULT_THEME,
        )
        assert "# Legend" in result

    def test_diagram_style_returns_mermaid(self):
        result = render_legend_only(
            legend_style="diagram",
            legend_scale=1.0,
            markdown=False,
            theme=DEFAULT_THEME,
        )
        assert "graph" in result or "flowchart" in result

    def test_markdown_wraps_in_code_block(self):
        result = render_legend_only(
            legend_style="diagram",
            legend_scale=1.0,
            markdown=True,
            theme=DEFAULT_THEME,
        )
        assert "```mermaid" in result
        assert "```" in result

    def test_compact_with_markdown(self):
        result = render_legend_only(
            legend_style="compact",
            legend_scale=1.0,
            markdown=True,
            theme=DEFAULT_THEME,
        )
        assert "```mermaid" in result
