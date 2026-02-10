"""Shared SVG defs, theming, and configuration dataclasses."""

from __future__ import annotations

import base64
import functools
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SvgTheme:
    """Color and styling theme for SVG diagrams.

    Each color field is a CSS color string. Node colors are ``(fill, stroke)``
    tuples. Load from YAML with :func:`~unifi_network_maps.render.resolve_themes`.
    """

    # Links
    link_standard: tuple[str, str]
    link_poe: tuple[str, str]

    # Nodes - infrastructure
    node_gateway: tuple[str, str]
    node_switch: tuple[str, str]
    node_ap: tuple[str, str]
    node_client: tuple[str, str]
    node_other: tuple[str, str]
    node_client_cluster: tuple[str, str] = ("#d4b8ff", "#a080e0")

    # Nodes - extended device types
    node_camera: tuple[str, str] = ("#b3e5fc", "#64b5f6")  # Light blue
    node_tv: tuple[str, str] = ("#d1c4e9", "#9575cd")  # Light violet
    node_phone: tuple[str, str] = ("#c8e6c9", "#81c784")  # Light green
    node_printer: tuple[str, str] = ("#cfd8dc", "#90a4ae")  # Blue-gray
    node_nas: tuple[str, str] = ("#ffe0b2", "#ffb74d")  # Amber
    node_speaker: tuple[str, str] = ("#b2dfdb", "#4db6ac")  # Teal
    node_game_console: tuple[str, str] = ("#e1bee7", "#ba68c8")  # Light purple
    node_iot: tuple[str, str] = ("#b2ebf2", "#4dd0e1")  # Cyan

    # Groups
    group_fill: str = "#f8f9fa"
    group_stroke: str = "#dee2e6"
    group_radius: int = 8
    group_label_fill: str = "#495057"
    group_stroke_width: int = 2

    # VLANs
    vlan_colors: dict[int, str] = field(default_factory=dict)

    # Background & text
    background: str = "#ffffff"
    text_primary: str = "#1a1a1a"
    text_secondary: str = "#1a1a1a"

    # Status indicators
    status_online: str = "#00a86b"
    status_offline: str = "#ef4444"

    # WAN globe
    wan_globe: tuple[str, str] = ("#4fc3f7", "#0288d1")
    wan_background: str = "#f0f9ff"  # Light blue tint for WAN box

    # PoE indicator
    poe_fill: str = "#1565c0"  # Dark blue
    poe_stroke: str = "#ffc107"  # Golden

    # Icon set
    icon_set: str = "isometric"

    # Font
    font_family: str | None = None

    # Icon decal color (for modern icons rendered on node surface)
    icon_decal: str = "#5A6878"

    # Isometric grid
    grid_color: str = "#efefef"

    # Isometric node side face colors (SW=left, E=right)
    node_side_left: str = "#dcdcdc"
    node_side_right: str = "#c8c8c8"

    def group_colors(self, group_name: str) -> tuple[str, str]:
        """Return (fill, stroke) colors for a group based on its type."""
        color_map = {
            "gateway": self.node_gateway,
            "switch": self.node_switch,
            "ap": self.node_ap,
            "client": self.node_client,
            "client_cluster": self.node_client_cluster,
            "camera": self.node_camera,
            "tv": self.node_tv,
            "phone": self.node_phone,
            "printer": self.node_printer,
            "nas": self.node_nas,
            "speaker": self.node_speaker,
            "game_console": self.node_game_console,
            "iot": self.node_iot,
            "other": self.node_other,
        }
        return color_map.get(group_name.lower(), (self.group_fill, self.group_stroke))

    def vlan_color(self, vlan_id: int) -> str:
        """Return color for a VLAN, using theme color or auto-generated fallback."""
        if vlan_id in self.vlan_colors:
            return self.vlan_colors[vlan_id]
        # Golden angle HSL rotation for distinct, deterministic colors
        hue = (vlan_id * 137) % 360
        return f"hsl({hue}, 70%, 55%)"


DEFAULT_THEME = SvgTheme(
    link_standard=("#16a085", "#2ecc71"),
    link_poe=("#1e88e5", "#42a5f5"),
    node_gateway=("#ffd199", "#ffb15a"),
    node_switch=("#bfe4ff", "#8ac6ff"),
    node_ap=("#c4f2d4", "#8ee3b4"),
    node_client=("#e4ccff", "#c5a4ff"),
    node_other=("#e3e3e3", "#cfcfcf"),
)


def _gradient(grad_id: str, colors: tuple[str, str], *, horizontal: bool = False) -> str:
    """Build a single linearGradient element."""
    x2, y2 = ("100%", "0%") if horizontal else ("100%", "100%")
    return (
        f'<linearGradient id="{grad_id}" x1="0%" y1="0%" x2="{x2}" y2="{y2}">'
        f'<stop offset="0%" stop-color="{colors[0]}"/>'
        f'<stop offset="100%" stop-color="{colors[1]}"/>'
        "</linearGradient>"
    )


def svg_defs(prefix: str, theme: SvgTheme = DEFAULT_THEME) -> str:
    gradient_prefix = f"{prefix}-" if prefix else ""
    node_prefix = f"{prefix}-node-" if prefix else "node-"
    filter_prefix = f"{prefix}-" if prefix else ""

    parts = ["<defs>"]

    # Link gradients (horizontal)
    parts.append(_gradient(f"{gradient_prefix}link-standard", theme.link_standard, horizontal=True))
    parts.append(_gradient(f"{gradient_prefix}link-poe", theme.link_poe, horizontal=True))

    # Node gradients (diagonal)
    node_types: list[tuple[str, tuple[str, str]]] = [
        ("gateway", theme.node_gateway),
        ("switch", theme.node_switch),
        ("ap", theme.node_ap),
        ("client", theme.node_client),
        ("client_cluster", theme.node_client_cluster),
        ("other", theme.node_other),
        ("camera", theme.node_camera),
        ("tv", theme.node_tv),
        ("phone", theme.node_phone),
        ("printer", theme.node_printer),
        ("nas", theme.node_nas),
        ("speaker", theme.node_speaker),
        ("game_console", theme.node_game_console),
        ("iot", theme.node_iot),
    ]
    for name, colors in node_types:
        parts.append(_gradient(f"{node_prefix}{name}", colors))

    # Filters
    parts.append(
        f'<filter id="{filter_prefix}edge-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="4" result="blur"/>'
        "</filter>"
    )
    # Emboss filter for icon decals - iOS glass effect
    parts.append(
        f'<filter id="{filter_prefix}icon-emboss" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="2.5" result="blur"/>'
        '<feOffset in="blur" dx="0" dy="2.5" result="dropShadow"/>'
        '<feFlood flood-color="#000000" flood-opacity="0.4" result="shadowColor"/>'
        '<feComposite in="shadowColor" in2="dropShadow" operator="in" result="shadow"/>'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="1.5" result="blurLight"/>'
        '<feOffset in="blurLight" dx="-2" dy="-1.8" result="lightOffset"/>'
        '<feFlood flood-color="#ffffff" flood-opacity="0.9" result="lightColor"/>'
        '<feComposite in="lightColor" in2="lightOffset" operator="in" result="highlight"/>'
        '<feComposite in="highlight" in2="SourceAlpha" operator="out" result="edgeHighlight"/>'
        '<feGaussianBlur in="SourceAlpha" stdDeviation="1.5" result="blurDark"/>'
        '<feOffset in="blurDark" dx="2" dy="1.8" result="darkOffset"/>'
        '<feFlood flood-color="#000000" flood-opacity="0.6" result="darkColor"/>'
        '<feComposite in="darkColor" in2="darkOffset" operator="in" result="innerShadow"/>'
        '<feComposite in="innerShadow" in2="SourceAlpha" operator="out" result="edgeShadow"/>'
        "<feMerge>"
        '<feMergeNode in="shadow"/>'
        '<feMergeNode in="edgeHighlight"/>'
        '<feMergeNode in="edgeShadow"/>'
        '<feMergeNode in="SourceGraphic"/>'
        "</feMerge>"
        "</filter>"
    )

    # Globe gradient and PoE bolt symbol
    parts.append(_gradient(f"{gradient_prefix}globe", theme.wan_globe))
    parts.append(
        f'<symbol id="{filter_prefix}poe-bolt" viewBox="0 0 24 24">'
        '<path fill-rule="evenodd" d="M14.615 1.595a.75.75 0 0 1 .359.852L12.982 9.75h7.268a.75.75 0 0 1 .548 1.262l-10.5 11.25a.75.75 0 0 1-1.272-.71l1.992-7.302H3.75a.75.75 0 0 1-.548-1.262l10.5-11.25a.75.75 0 0 1 .913-.143Z" clip-rule="evenodd"/>'
        "</symbol>"
    )
    parts.append("</defs>")

    return "".join(parts)


@dataclass(frozen=True)
class SvgOptions:
    """Configuration for SVG diagram rendering.

    Controls node dimensions, spacing, layout algorithm, and canvas size.
    Pass to :func:`render_svg` or :func:`render_svg_isometric` to customize output.
    """

    node_width: int = 160
    node_height: int = 48
    h_gap: int = 80
    v_gap: int = 80
    padding: int = 40
    font_size: int = 10
    icon_size: int = 18
    width: int | None = None
    height: int | None = None
    layout_mode: str = "physical"  # "physical" | "grouped"
    group_padding: int = 20
    group_gap: int = 40


_FONTS_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
_SYSTEM_FONT_STACK = "Arial,Helvetica,sans-serif"


@functools.lru_cache(maxsize=4)
def _build_font_style(font_family: str | None) -> tuple[str, str]:
    """Build @font-face CSS and font-family stack for the given font.

    Results are cached to avoid repeated disk I/O for the same font family.
    Returns (font_face_css, font_family_css) where font_face_css may be empty.
    """
    if not font_family:
        return "", _SYSTEM_FONT_STACK

    slug = font_family.lower().replace(" ", "-")
    font_face_parts: list[str] = []

    for weight, suffix in ((400, "regular"), (600, "semibold")):
        path = _FONTS_DIR / f"{slug}-{suffix}.woff2"
        if not path.exists():
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        font_face_parts.append(
            f"@font-face{{font-family:'{font_family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
        )

    if not font_face_parts:
        return "", _SYSTEM_FONT_STACK

    font_face_css = "".join(font_face_parts)
    family_css = f"'{font_family}',{_SYSTEM_FONT_STACK}"
    return font_face_css, family_css


def _svg_style_block(theme: SvgTheme, font_size: int, *, iso: bool = False) -> str:
    """Build the <style> element for an SVG, including optional @font-face."""
    font_face, family = _build_font_style(theme.font_family)
    parts = [f"<style>{font_face}"]

    if iso:
        parts.append(f"text{{font-family:{family};}}")
        parts.append(f"text:not(.group-label){{font-size:{font_size}px;}}")
    else:
        parts.append(f"text{{font-family:{family};font-size:{font_size}px;}}")

    parts.append("text.node-label{font-weight:600;}")
    parts.append("</style>")
    return "".join(parts)
