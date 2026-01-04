"""Mermaid theming helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MermaidTheme:
    node_gateway: tuple[str, str]
    node_switch: tuple[str, str]
    node_ap: tuple[str, str]
    node_client: tuple[str, str]
    node_other: tuple[str, str]
    poe_link: str
    poe_link_width: int
    poe_link_arrow: str
    standard_link: str
    standard_link_width: int
    standard_link_arrow: str


DEFAULT_THEME = MermaidTheme(
    node_gateway=("#ffe3b3", "#d98300"),
    node_switch=("#d6ecff", "#3a7bd5"),
    node_ap=("#d7f5e7", "#27ae60"),
    node_client=("#f2e5ff", "#7f3fbf"),
    node_other=("#eeeeee", "#8f8f8f"),
    poe_link="#1e88e5",
    poe_link_width=2,
    poe_link_arrow="none",
    standard_link="#2ecc71",
    standard_link_width=2,
    standard_link_arrow="none",
)


def class_defs(theme: MermaidTheme = DEFAULT_THEME) -> list[str]:
    return [
        f"  classDef node_gateway fill:{theme.node_gateway[0]},stroke:{theme.node_gateway[1]},stroke-width:1px;",
        f"  classDef node_switch fill:{theme.node_switch[0]},stroke:{theme.node_switch[1]},stroke-width:1px;",
        f"  classDef node_ap fill:{theme.node_ap[0]},stroke:{theme.node_ap[1]},stroke-width:1px;",
        f"  classDef node_client fill:{theme.node_client[0]},stroke:{theme.node_client[1]},stroke-width:1px;",
        f"  classDef node_other fill:{theme.node_other[0]},stroke:{theme.node_other[1]},stroke-width:1px;",
        "  classDef node_legend font-size:10px;",
    ]
