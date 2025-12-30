from unifi_mermaid.mermaid import render_mermaid
from unifi_mermaid.topology import Edge, build_rank_edges_by_topology, build_rank_edges_by_type


def test_rank_edges_by_type_links_groups():
    groups = {"gateway": ["GW"], "switch": ["SW"], "ap": [], "other": []}
    edges = build_rank_edges_by_type(groups, ["gateway", "switch", "ap", "other"])
    assert edges == [("GW", "SW")]


def test_rank_edges_by_topology_uses_hops():
    edges = [Edge("GW", "SW"), Edge("SW", "AP")]
    ranks = build_rank_edges_by_topology(edges, ["GW"])
    assert ("GW", "SW") in ranks


def test_render_mermaid_hides_rank_edges():
    edges = [Edge("GW", "SW")]
    output = render_mermaid(edges, rank_edges=[("GW", "SW")])
    assert "linkStyle" in output
