"""Mermaid diagram rendering."""

from __future__ import annotations

from collections.abc import Iterable

from .topology import Edge


def _escape(label: str) -> str:
    return label.replace('"', '\\"')


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


def render_mermaid(
    edges: Iterable[Edge],
    direction: str = "LR",
    *,
    groups: dict[str, list[str]] | None = None,
    group_order: list[str] | None = None,
    node_types: dict[str, str] | None = None,
) -> str:
    edge_list = list(edges)
    group_nodes: list[str] = []
    if groups:
        for members in groups.values():
            group_nodes.extend(members)
    id_map = _build_id_map(edge_list, group_nodes)
    lines = [
        '%%{init: {"flowchart": {"curve": "linear", "defaultRenderer": "dagre"}}}%%',
        f"graph {direction}",
    ]
    poe_links: list[int] = []
    link_index = 0
    if groups:
        ordered = group_order or list(groups.keys())
        for group_name in ordered:
            members = groups.get(group_name, [])
            if not members:
                continue
            group_id = _slugify(f"group_{group_name}")
            label = group_name.replace("_", " ").title()
            lines.append(f'  subgraph {group_id}["{_escape(label)}"]')
            for member in members:
                lines.append(f"    {_node_ref(member, id_map[member])}")
            lines.append("  end")
    use_node_labels = not groups
    for edge in edge_list:
        if use_node_labels:
            left = _node_ref(edge.left, id_map[edge.left])
            right = _node_ref(edge.right, id_map[edge.right])
        else:
            left = id_map[edge.left]
            right = id_map[edge.right]
        if edge.label:
            label = _escape(edge.label)
            lines.append(f'  {left} ---|"{label}"| {right}')
        else:
            lines.append(f"  {left} --- {right}")
        if edge.poe:
            poe_links.append(link_index)
        link_index += 1
    if node_types:
        class_map = {
            "gateway": "node_gateway",
            "switch": "node_switch",
            "ap": "node_ap",
            "client": "node_client",
            "other": "node_other",
        }
        if node_types:
            for name, node_type in node_types.items():
                class_name = class_map.get(node_type, "node_other")
                node_id = id_map.get(name)
                if node_id:
                    lines.append(f"  class {node_id} {class_name}")
        lines.append("  classDef node_gateway fill:#ffe3b3,stroke:#d98300,stroke-width:1px")
        lines.append("  classDef node_switch fill:#d6ecff,stroke:#3a7bd5,stroke-width:1px")
        lines.append("  classDef node_ap fill:#d7f5e7,stroke:#27ae60,stroke-width:1px")
        lines.append("  classDef node_client fill:#f2e5ff,stroke:#7f3fbf,stroke-width:1px")
        lines.append("  classDef node_other fill:#eeeeee,stroke:#8f8f8f,stroke-width:1px")
    for index in poe_links:
        lines.append(f"  linkStyle {index} stroke:#1e88e5,stroke-width:2px")
    return "\n".join(lines) + "\n"


def render_legend() -> str:
    lines = [
        "graph TB",
        '  subgraph legend["Legend"];',
        '    legend_gateway["Gateway"];',
        '    legend_switch["Switch"];',
        '    legend_ap["AP"];',
        '    legend_client["Client"];',
        '    legend_other["Other"];',
        '    legend_poe_a["PoE Link A"];',
        '    legend_poe_b["PoE Link B"];',
        '    legend_no_poe_a["Link A"];',
        '    legend_no_poe_b["Link B"];',
        "    legend_poe_a ---|⚡| legend_poe_b;",
        "    legend_no_poe_a --- legend_no_poe_b;",
        "    linkStyle 0 arrowhead:none;",
        "    linkStyle 1 arrowhead:none;",
        "  end",
        "  class legend_gateway node_gateway;",
        "  class legend_switch node_switch;",
        "  class legend_ap node_ap;",
        "  class legend_client node_client;",
        "  class legend_other node_other;",
        "  class legend_poe_a node_legend;",
        "  class legend_poe_b node_legend;",
        "  class legend_no_poe_a node_legend;",
        "  class legend_no_poe_b node_legend;",
        "  classDef node_gateway fill:#ffe3b3,stroke:#d98300,stroke-width:1px;",
        "  classDef node_switch fill:#d6ecff,stroke:#3a7bd5,stroke-width:1px;",
        "  classDef node_ap fill:#d7f5e7,stroke:#27ae60,stroke-width:1px;",
        "  classDef node_client fill:#f2e5ff,stroke:#7f3fbf,stroke-width:1px;",
        "  classDef node_other fill:#eeeeee,stroke:#8f8f8f,stroke-width:1px;",
        "  classDef node_legend font-size:10px;",
    ]
    lines.append("  linkStyle 0 stroke:#1e88e5,stroke-width:2px,arrowhead:none;")
    lines.append("  linkStyle 1 stroke:#2ecc71,stroke-width:2px,arrowhead:none;")
    return "\n".join(lines) + "\n"
