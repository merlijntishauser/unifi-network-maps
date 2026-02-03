"""Theme loading for Mermaid and SVG rendering."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..io.paths import resolve_theme_path
from .mermaid_theme import DEFAULT_THEME as DEFAULT_MERMAID_THEME
from .mermaid_theme import MermaidTheme
from .svg_theme import DEFAULT_THEME as DEFAULT_SVG_THEME
from .svg_theme import SvgTheme

# Built-in theme names mapped to YAML files in assets/themes/
BUILTIN_THEMES = {
    "unifi": "unifi.yaml",
    "unifi-dark": "unifi-dark.yaml",
    "minimal": "minimal.yaml",
    "classic": "default.yaml",
    "classic-dark": "dark.yaml",
}

_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "themes"


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


def _coerce_vlan_colors(value: object) -> dict[int, str]:
    """Parse vlan_colors from theme YAML."""
    if not isinstance(value, dict):
        return {}
    result: dict[int, str] = {}
    for key, color in value.items():
        if isinstance(color, str):
            if isinstance(key, int):
                result[key] = color
            elif isinstance(key, str) and key.isdigit():
                result[int(key)] = color
    return result


def _coerce_icon_set(value: object, default: str) -> str:
    """Parse icon_set from theme YAML."""
    if isinstance(value, str) and value in ("legacy", "modern", "flat", "outline"):
        return value
    return default


def _svg_theme_from_dict(data: dict, base: SvgTheme) -> SvgTheme:
    nodes = data.get("nodes", {}) if isinstance(data.get("nodes"), dict) else {}
    links = data.get("links", {}) if isinstance(data.get("links"), dict) else {}
    text = data.get("text", {}) if isinstance(data.get("text"), dict) else {}
    status = data.get("status", {}) if isinstance(data.get("status"), dict) else {}

    return SvgTheme(
        link_standard=_coerce_pair(links.get("standard"), base.link_standard),
        link_poe=_coerce_pair(links.get("poe"), base.link_poe),
        node_gateway=_coerce_pair(nodes.get("gateway"), base.node_gateway),
        node_switch=_coerce_pair(nodes.get("switch"), base.node_switch),
        node_ap=_coerce_pair(nodes.get("ap"), base.node_ap),
        node_client=_coerce_pair(nodes.get("client"), base.node_client),
        node_other=_coerce_pair(nodes.get("other"), base.node_other),
        vlan_colors=_coerce_vlan_colors(data.get("vlan_colors")),
        background=_coerce_color(data.get("background"), base.background),
        text_primary=_coerce_color(text.get("primary"), base.text_primary),
        text_secondary=_coerce_color(text.get("secondary"), base.text_secondary),
        status_online=_coerce_color(status.get("online"), base.status_online),
        status_offline=_coerce_color(status.get("offline"), base.status_offline),
        wan_globe=_coerce_pair(data.get("wan_globe"), base.wan_globe),
        wan_background=_coerce_color(data.get("wan_background"), base.wan_background),
        poe_fill=_coerce_color(data.get("poe_fill"), base.poe_fill),
        poe_stroke=_coerce_color(data.get("poe_stroke"), base.poe_stroke),
        icon_set=_coerce_icon_set(data.get("icon_set"), base.icon_set),
        icon_decal=_coerce_color(data.get("icon_decal"), base.icon_decal),
        node_side_left=_coerce_color(data.get("node_side_left"), base.node_side_left),
        node_side_right=_coerce_color(data.get("node_side_right"), base.node_side_right),
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
        builtin_path = _ASSETS_DIR / BUILTIN_THEMES[theme_name]
        return load_theme(builtin_path)
    return DEFAULT_MERMAID_THEME, DEFAULT_SVG_THEME
