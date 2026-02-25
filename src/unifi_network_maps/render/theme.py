"""Theme loading for Mermaid and SVG rendering."""

from __future__ import annotations

from pathlib import Path

import yaml
from unifi_topology.render.svg_theme import DEFAULT_THEME as DEFAULT_SVG_THEME
from unifi_topology.render.svg_theme import SvgTheme
from unifi_topology.render.theme import (
    BUILTIN_THEMES,
    builtin_theme_yaml_path,
    resolve_svg_themes,
)

from ..io.paths import resolve_theme_path
from .mermaid_theme import DEFAULT_THEME as DEFAULT_MERMAID_THEME
from .mermaid_theme import MermaidTheme


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
        node_wan=_node("wan"),
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


def _load_mermaid_theme_from_yaml(theme_path: Path) -> MermaidTheme:
    """Load Mermaid theme from a YAML file."""
    payload = yaml.safe_load(theme_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Theme file must contain a YAML mapping")
    mermaid_data = payload.get("mermaid", {})
    return _mermaid_theme_from_dict(mermaid_data, DEFAULT_MERMAID_THEME)


def load_theme(path: str | Path) -> tuple[MermaidTheme, SvgTheme]:
    """Load a custom theme from a user-provided file path.

    The path is validated to be within allowed directories for security.
    For built-in themes, use resolve_themes(theme_name=...) instead.
    """
    theme_path = resolve_theme_path(path, require_exists=False)
    mermaid_theme = _load_mermaid_theme_from_yaml(theme_path)
    svg_theme = resolve_svg_themes(theme_file=theme_path)
    return mermaid_theme, svg_theme


def resolve_themes(
    theme_name: str | None = None,
    theme_file: str | Path | None = None,
) -> tuple[MermaidTheme, SvgTheme]:
    """Resolve theme from name or file path.

    Args:
        theme_name: Built-in theme name (e.g., "unifi", "classic").
        theme_file: Custom theme file path. Takes priority over theme_name.

    Returns:
        Tuple of (MermaidTheme, SvgTheme).
    """
    if theme_file:
        return load_theme(theme_file)
    if theme_name:
        if theme_name not in BUILTIN_THEMES:
            valid = ", ".join(sorted(BUILTIN_THEMES.keys()))
            raise ValueError(f"Unknown theme: {theme_name}. Valid themes: {valid}")
        builtin_path = builtin_theme_yaml_path(theme_name)
        mermaid_theme = _load_mermaid_theme_from_yaml(builtin_path)
        svg_theme = resolve_svg_themes(theme_name=theme_name)
        return mermaid_theme, svg_theme
    return DEFAULT_MERMAID_THEME, DEFAULT_SVG_THEME
