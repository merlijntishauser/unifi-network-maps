from unifi_network_maps.model.topology import (
    Device,
    Edge,
    build_tree_edges_by_topology,
    classify_device_type,
    group_devices_by_type,
)
from unifi_network_maps.render.mermaid import render_mermaid


def test_classify_gateway_type():
    device = Device(
        name="Gateway", model_name="", model="", mac="aa", ip="", type="gateway", lldp_info=[]
    )
    assert classify_device_type(device) == "gateway"


def test_group_devices_by_type_includes_ap():
    devices = [
        Device(name="AP One", model_name="", model="", mac="aa", ip="", type="uap", lldp_info=[])
    ]
    groups = group_devices_by_type(devices)
    assert groups["ap"] == ["AP One"]


def test_render_mermaid_with_groups_uses_subgraph():
    edges = [Edge("Gateway", "Switch")]
    groups = {"gateway": ["Gateway"], "switch": ["Switch"], "ap": [], "other": []}
    output = render_mermaid(edges, groups=groups, group_order=["gateway", "switch", "ap", "other"])
    assert 'subgraph group_gateway["Gateway"]' in output


def test_rank_edges_by_topology_uses_hops():
    edges = [Edge("GW", "SW"), Edge("SW", "AP")]
    tree_edges = build_tree_edges_by_topology(edges, ["GW"])
    assert {edge.left: edge.right for edge in tree_edges} == {"GW": "SW", "SW": "AP"}
