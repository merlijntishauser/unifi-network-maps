"""Shared SVG defs and theming."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SvgTheme:
    # Links
    link_standard: tuple[str, str]
    link_poe: tuple[str, str]

    # Nodes
    node_gateway: tuple[str, str]
    node_switch: tuple[str, str]
    node_ap: tuple[str, str]
    node_client: tuple[str, str]
    node_other: tuple[str, str]
    node_client_cluster: tuple[str, str] = ("#d4b8ff", "#a080e0")

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
    text_secondary: str = "#6b7280"

    # Status indicators
    status_online: str = "#00a86b"
    status_offline: str = "#ef4444"

    # WAN globe
    wan_globe: tuple[str, str] = ("#4fc3f7", "#0288d1")
    wan_background: str = "#f0f9ff"  # Light blue tint for WAN box

    # Icon set
    icon_set: str = "legacy"

    # Icon decal color (for modern icons rendered on node surface)
    icon_decal: str = "#5A6878"

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


def svg_defs(prefix: str, theme: SvgTheme = DEFAULT_THEME) -> str:
    gradient_prefix = f"{prefix}-" if prefix else ""
    node_prefix = f"{prefix}-node-" if prefix else "node-"
    filter_prefix = f"{prefix}-" if prefix else ""
    return (
        "<defs>"
        f'<linearGradient id="{gradient_prefix}link-standard" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{theme.link_standard[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.link_standard[1]}"/>'
        "</linearGradient>"
        f'<linearGradient id="{gradient_prefix}link-poe" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{theme.link_poe[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.link_poe[1]}"/>'
        "</linearGradient>"
        f'<linearGradient id="{node_prefix}gateway" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.node_gateway[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.node_gateway[1]}"/>'
        "</linearGradient>"
        f'<linearGradient id="{node_prefix}switch" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.node_switch[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.node_switch[1]}"/>'
        "</linearGradient>"
        f'<linearGradient id="{node_prefix}ap" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.node_ap[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.node_ap[1]}"/>'
        "</linearGradient>"
        f'<linearGradient id="{node_prefix}client" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.node_client[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.node_client[1]}"/>'
        "</linearGradient>"
        f'<linearGradient id="{node_prefix}client_cluster" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.node_client_cluster[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.node_client_cluster[1]}"/>'
        "</linearGradient>"
        f'<linearGradient id="{node_prefix}other" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.node_other[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.node_other[1]}"/>'
        "</linearGradient>"
        f'<filter id="{filter_prefix}edge-glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="4" result="blur"/>'
        "</filter>"
        # Emboss filter for icon decals - iOS glass effect
        f'<filter id="{filter_prefix}icon-emboss" x="-50%" y="-50%" width="200%" height="200%">'
        # Outer glow/shadow for depth
        '<feGaussianBlur in="SourceAlpha" stdDeviation="1.5" result="blur"/>'
        '<feOffset in="blur" dx="0" dy="1.5" result="dropShadow"/>'
        '<feFlood flood-color="#000000" flood-opacity="0.25" result="shadowColor"/>'
        '<feComposite in="shadowColor" in2="dropShadow" operator="in" result="shadow"/>'
        # Top highlight edge (outside the icon)
        '<feGaussianBlur in="SourceAlpha" stdDeviation="1" result="blurLight"/>'
        '<feOffset in="blurLight" dx="-1.5" dy="-1.2" result="lightOffset"/>'
        '<feFlood flood-color="#ffffff" flood-opacity="0.8" result="lightColor"/>'
        '<feComposite in="lightColor" in2="lightOffset" operator="in" result="highlight"/>'
        # Subtract original shape from highlight to keep only edge glow
        '<feComposite in="highlight" in2="SourceAlpha" operator="out" result="edgeHighlight"/>'
        # Bottom shadow edge (outside the icon)
        '<feGaussianBlur in="SourceAlpha" stdDeviation="1" result="blurDark"/>'
        '<feOffset in="blurDark" dx="1.5" dy="1.2" result="darkOffset"/>'
        '<feFlood flood-color="#000000" flood-opacity="0.5" result="darkColor"/>'
        '<feComposite in="darkColor" in2="darkOffset" operator="in" result="innerShadow"/>'
        # Subtract original shape from shadow to keep only edge shadow
        '<feComposite in="innerShadow" in2="SourceAlpha" operator="out" result="edgeShadow"/>'
        # Combine: edges first, then full-strength icon on top
        "<feMerge>"
        '<feMergeNode in="shadow"/>'
        '<feMergeNode in="edgeHighlight"/>'
        '<feMergeNode in="edgeShadow"/>'
        '<feMergeNode in="SourceGraphic"/>'
        "</feMerge>"
        "</filter>"
        f'<linearGradient id="{gradient_prefix}globe" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.wan_globe[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.wan_globe[1]}"/>'
        "</linearGradient>"
        "</defs>"
    )
