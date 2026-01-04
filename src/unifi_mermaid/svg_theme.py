"""Shared SVG defs and theming."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SvgTheme:
    link_standard: tuple[str, str]
    link_poe: tuple[str, str]
    node_gateway: tuple[str, str]
    node_switch: tuple[str, str]
    node_ap: tuple[str, str]
    node_client: tuple[str, str]
    node_other: tuple[str, str]


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
        f'<linearGradient id="{node_prefix}other" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{theme.node_other[0]}"/>'
        f'<stop offset="100%" stop-color="{theme.node_other[1]}"/>'
        "</linearGradient>"
        "</defs>"
    )
