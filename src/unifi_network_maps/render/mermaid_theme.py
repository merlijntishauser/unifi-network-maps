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
    node_text: str | None = None
    edge_label_border: str | None = None
    edge_label_border_width: int | None = None


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
    node_text=None,
    edge_label_border=None,
    edge_label_border_width=None,
)


def class_defs(theme: MermaidTheme = DEFAULT_THEME) -> list[str]:
    def node_def(name: str, fill: str, stroke: str) -> str:
        color = f",color:{theme.node_text}" if theme.node_text else ""
        return f"  classDef {name} fill:{fill},stroke:{stroke},stroke-width:1px{color};"

    return [
        node_def("node_gateway", theme.node_gateway[0], theme.node_gateway[1]),
        node_def("node_switch", theme.node_switch[0], theme.node_switch[1]),
        node_def("node_ap", theme.node_ap[0], theme.node_ap[1]),
        node_def("node_client", theme.node_client[0], theme.node_client[1]),
        node_def("node_other", theme.node_other[0], theme.node_other[1]),
        "  classDef node_legend font-size:10px;",
    ]
