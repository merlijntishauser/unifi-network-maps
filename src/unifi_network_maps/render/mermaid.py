"""Mermaid diagram rendering."""

from __future__ import annotations

import json
from collections.abc import Iterable

from ..model.topology import Edge
from .mermaid_theme import DEFAULT_THEME, MermaidTheme, class_defs
from .templating import render_template


def _escape(label: str) -> str:
    normalized = label.replace("\r\n", "\n").replace("\r", "\n")
    escaped = normalized.replace("\\", "\\\\").replace("\n", "\\n")
    return escaped.replace('"', '\\"')


def _slugify(value: str) -> str:
    normalized = []
    for ch in value.strip():
        if ch.isalnum():
            normalized.append(ch.lower())
        else:
            normalized.append("_")
    slug = "".join(normalized).strip("_")
    if not slug or slug[0].isdigit():
        slug = f"n_{slug}" if slug else "n"
    return slug


def _build_id_map(edges: Iterable[Edge], nodes: Iterable[str]) -> dict[str, str]:
    id_map: dict[str, str] = {}
    used: set[str] = set()

    def assign(name: str) -> None:
        if name in id_map:
            return
        base = _slugify(name)
        candidate = base
        counter = 2
        while candidate in used:
            candidate = f"{base}_{counter}"
            counter += 1
        id_map[name] = candidate
        used.add(candidate)

    for node in nodes:
        assign(node)
    for edge in edges:
        assign(edge.left)
        assign(edge.right)

    return id_map


def _node_ref(name: str, node_id: str) -> str:
    return f'{node_id}["{_escape(name)}"]'


def _group_nodes(groups: dict[str, list[str]] | None) -> list[str]:
    if not groups:
        return []
    nodes: list[str] = []
    for members in groups.values():
        nodes.extend(members)
    return nodes


def _render_group_sections(
    lines: list[str],
    groups: dict[str, list[str]],
    *,
    group_order: list[str] | None,
    id_map: dict[str, str],
) -> None:
    ordered = group_order or list(groups.keys())
    for group_name in ordered:
        members = groups.get(group_name, [])
        if not members:
            continue
        group_id = _slugify(f"group_{group_name}")
        label = group_name.replace("_", " ").title()
        lines.append(f'  subgraph {group_id}["{_escape(label)}"];')
        for member in members:
            lines.append(f"    {_node_ref(member, id_map[member])};")
        lines.append("  end")


def _render_edge_lines(
    lines: list[str],
    edges: list[Edge],
    *,
    id_map: dict[str, str],
    use_node_labels: bool,
) -> tuple[list[int], list[int]]:
    poe_links: list[int] = []
    wireless_links: list[int] = []
    for index, edge in enumerate(edges):
        if use_node_labels:
            left = _node_ref(edge.left, id_map[edge.left])
            right = _node_ref(edge.right, id_map[edge.right])
        else:
            left = id_map[edge.left]
            right = id_map[edge.right]
        if edge.label:
            label = _escape(edge.label)
            lines.append(f'  {left} ---|"{label}"| {right};')
        else:
            lines.append(f"  {left} --- {right};")
        if edge.poe:
            poe_links.append(index)
        if edge.wireless:
            wireless_links.append(index)
    return poe_links, wireless_links


def _render_node_classes(
    lines: list[str],
    *,
    node_types: dict[str, str],
    id_map: dict[str, str],
    theme: MermaidTheme,
) -> None:
    class_map = {
        "gateway": "node_gateway",
        "switch": "node_switch",
        "ap": "node_ap",
        "client": "node_client",
        "other": "node_other",
    }
    for name, node_type in node_types.items():
        class_name = class_map.get(node_type, "node_other")
        node_id = id_map.get(name)
        if node_id:
            lines.append(f"  class {node_id} {class_name};")
    lines.extend(class_defs(theme))


def _render_link_styles(
    lines: list[str],
    *,
    poe_links: list[int],
    wireless_links: list[int],
    theme: MermaidTheme,
) -> None:
    for index in poe_links:
        lines.append(
            "  linkStyle "
            f"{index} stroke:{theme.poe_link},stroke-width:{theme.poe_link_width}px,"
            f"arrowhead:{theme.poe_link_arrow};"
        )
    for index in wireless_links:
        lines.append(f"  linkStyle {index} stroke-dasharray: 5 4;")


def render_mermaid(
    edges: Iterable[Edge],
    direction: str = "LR",
    *,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    node_types: dict[str, str] | None = None,
    theme: MermaidTheme = DEFAULT_THEME,
) -> str:
    edge_list = list(edges)
    id_map = _build_id_map(edge_list, _group_nodes(groups))
    theme_vars: dict[str, object] = {}
    if theme.edge_label_border:
        theme_vars["edgeLabelBorderColor"] = theme.edge_label_border
    if theme.edge_label_border_width:
        theme_vars["edgeLabelBorderWidth"] = theme.edge_label_border_width
    lines = []
    if theme_vars:
        lines.append(f'%%{{init: {{"themeVariables": {json.dumps(theme_vars)}}}}}%%')
    lines.append(f"graph {direction}")
    if groups:
        _render_group_sections(lines, groups, group_order=group_order, id_map=id_map)
    use_node_labels = not groups
    poe_links, wireless_links = _render_edge_lines(
        lines, edge_list, id_map=id_map, use_node_labels=use_node_labels
    )
    if node_types:
        _render_node_classes(lines, node_types=node_types, id_map=id_map, theme=theme)
    _render_link_styles(lines, poe_links=poe_links, wireless_links=wireless_links, theme=theme)
    return "\n".join(lines) + "\n"


def render_legend(theme: MermaidTheme = DEFAULT_THEME, *, legend_scale: float = 1.0) -> str:
    scale = legend_scale if legend_scale > 0 else 1.0
    legend_font_size = max(7, round(10 * scale))
    poe_link_width = max(1, round(theme.poe_link_width * scale))
    standard_link_width = max(1, round(theme.standard_link_width * scale))
    node_spacing = max(10, round(50 * scale))
    rank_spacing = max(10, round(50 * scale))
    node_padding = max(4, round(12 * scale))
    return (
        render_template(
            "mermaid_legend.mmd.j2",
            node_spacing=node_spacing,
            rank_spacing=rank_spacing,
            legend_font_size=legend_font_size,
            node_padding=node_padding,
            class_defs="\n".join(class_defs(theme)),
            poe_link=theme.poe_link,
            poe_link_width=poe_link_width,
            poe_link_arrow=theme.poe_link_arrow,
            standard_link=theme.standard_link,
            standard_link_width=standard_link_width,
            standard_link_arrow=theme.standard_link_arrow,
        ).rstrip()
        + "\n"
    )


def render_legend_compact(theme: MermaidTheme = DEFAULT_THEME) -> str:
    rows = [
        {
            "kind": "swatch",
            "fill": theme.node_gateway[0],
            "stroke": theme.node_gateway[1],
            "label": "Gateway",
        },
        {
            "kind": "swatch",
            "fill": theme.node_switch[0],
            "stroke": theme.node_switch[1],
            "label": "Switch",
        },
        {
            "kind": "swatch",
            "fill": theme.node_ap[0],
            "stroke": theme.node_ap[1],
            "label": "AP",
        },
        {
            "kind": "swatch",
            "fill": theme.node_client[0],
            "stroke": theme.node_client[1],
            "label": "Client",
        },
        {
            "kind": "swatch",
            "fill": theme.node_other[0],
            "stroke": theme.node_other[1],
            "label": "Other",
        },
        {
            "kind": "line",
            "color": theme.poe_link,
            "width": max(1, theme.poe_link_width),
            "dashed": False,
            "label": "PoE",
            "bolt": True,
        },
        {
            "kind": "line",
            "color": theme.standard_link,
            "width": max(1, theme.standard_link_width),
            "dashed": False,
            "label": "Link",
            "bolt": False,
        },
        {
            "kind": "line",
            "color": theme.standard_link,
            "width": max(1, theme.standard_link_width),
            "dashed": True,
            "label": "Wireless",
            "bolt": False,
        },
    ]
    return render_template("legend_compact.html.j2", rows=rows)
