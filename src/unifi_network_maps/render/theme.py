"""Theme loading for Mermaid and SVG rendering."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..io.paths import resolve_theme_path
from .mermaid_theme import DEFAULT_THEME as DEFAULT_MERMAID_THEME
from .mermaid_theme import MermaidTheme
from .svg_theme import DEFAULT_THEME as DEFAULT_SVG_THEME
from .svg_theme import SvgTheme


def _coerce_pair(value: object, default: tuple[str, str]) -> tuple[str, str]:
    if isinstance(value, list | tuple) and len(value) == 2:
        left, right = value
        if isinstance(left, str) and isinstance(right, str):
            return (left, right)
    if isinstance(value, dict):
        left = value.get("from") or value.get("start")
        right = value.get("to") or value.get("end")
        if isinstance(left, str) and isinstance(right, str):
            return (left, right)
    return default


def _coerce_color(value: object, default: str) -> str:
    return value if isinstance(value, str) else default


def _coerce_optional_color(value: object, default: str | None) -> str | None:
    return value if isinstance(value, str) else default


def _coerce_optional_int(value: object, default: int | None) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return default


def _mermaid_theme_from_dict(data: dict, base: MermaidTheme) -> MermaidTheme:
    nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}

    def _node(name: str) -> tuple[str, str]:
        return (
            _coerce_color(nodes.get(name, {}).get("fill"), getattr(base, f"node_{name}")[0]),
            _coerce_color(nodes.get(name, {}).get("stroke"), getattr(base, f"node_{name}")[1]),
        )

    return MermaidTheme(
        node_gateway=_node("gateway"),
        node_switch=_node("switch"),
        node_ap=_node("ap"),
        node_client=_node("client"),
        node_other=_node("other"),
        poe_link=_coerce_color(data.get("poe_link"), base.poe_link),
        poe_link_width=int(data.get("poe_link_width", base.poe_link_width)),
        poe_link_arrow=_coerce_color(data.get("poe_link_arrow"), base.poe_link_arrow),
        standard_link=_coerce_color(data.get("standard_link"), base.standard_link),
        standard_link_width=int(data.get("standard_link_width", base.standard_link_width)),
        standard_link_arrow=_coerce_color(
            data.get("standard_link_arrow"), base.standard_link_arrow
        ),
        node_text=_coerce_optional_color(data.get("node_text"), base.node_text),
        edge_label_border=_coerce_optional_color(
            data.get("edge_label_border"), base.edge_label_border
        ),
        edge_label_border_width=_coerce_optional_int(
            data.get("edge_label_border_width"), base.edge_label_border_width
        ),
    )


def _svg_theme_from_dict(data: dict, base: SvgTheme) -> SvgTheme:
    nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}
    links = data.get("links", {}) if isinstance(data.get("links"), dict) else {}

    return SvgTheme(
        link_standard=_coerce_pair(links.get("standard"), base.link_standard),
        link_poe=_coerce_pair(links.get("poe"), base.link_poe),
        node_gateway=_coerce_pair(nodes.get("gateway"), base.node_gateway),
        node_switch=_coerce_pair(nodes.get("switch"), base.node_switch),
        node_ap=_coerce_pair(nodes.get("ap"), base.node_ap),
        node_client=_coerce_pair(nodes.get("client"), base.node_client),
        node_other=_coerce_pair(nodes.get("other"), base.node_other),
    )


def load_theme(path: str | Path) -> tuple[MermaidTheme, SvgTheme]:
    theme_path = resolve_theme_path(path, require_exists=False)
    payload = yaml.safe_load(theme_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Theme file must contain a YAML mapping")

    mermaid_data = payload.get("mermaid", {})
    svg_data = payload.get("svg", {})

    mermaid_theme = _mermaid_theme_from_dict(mermaid_data, DEFAULT_MERMAID_THEME)
    svg_theme = _svg_theme_from_dict(svg_data, DEFAULT_SVG_THEME)
    return mermaid_theme, svg_theme


def resolve_themes(theme_file: str | Path | None) -> tuple[MermaidTheme, SvgTheme]:
    if theme_file:
        return load_theme(theme_file)
    return DEFAULT_MERMAID_THEME, DEFAULT_SVG_THEME
