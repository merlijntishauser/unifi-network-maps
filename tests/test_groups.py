from unifi_topology.model.classify import classify_device_type
from unifi_topology.model.edges import build_tree_edges_by_topology, group_devices_by_type
from unifi_topology.model.topology import Device, Edge
from unifi_topology.render.mermaid import render_mermaid


def test_classify_gateway_type():
    device = Device(
        name="Gateway", model_name="", model="", mac="aa", ip="", type="gateway", lldp_info=[]
    )
    assert classify_device_type(device) == "gateway"


def test_classify_ux_gateway_mode_true():
    device = Device(
        name="UXG Max", model_name="", model="UXG-Max", mac="aa", ip="", type="ux", lldp_info=[]
    )
    # in_gateway_mode not set (None) -- assume gateway
    assert classify_device_type(device) == "gateway"


def test_classify_ux_gateway_mode_false():
    """UX7 in AP mode should be classified as AP, not gateway."""
    device = Device(
        name="UX7",
        model_name="",
        model="U7-Pro",
        mac="bb",
        ip="",
        type="ux",
        lldp_info=[],
        in_gateway_mode=False,
    )
    assert classify_device_type(device) == "ap"


def test_classify_ux_gateway_mode_explicit_true():
    device = Device(
        name="UXG Max",
        model_name="",
        model="UXG-Max",
        mac="cc",
        ip="",
        type="ux",
        lldp_info=[],
        in_gateway_mode=True,
    )
    assert classify_device_type(device) == "gateway"


def test_classify_uxg_type_as_gateway():
    """UXG-series devices (UXG-Pro, UXG-Max/UXGB) report type 'uxg'."""
    device = Device(
        name="UXG Max",
        model_name="",
        model="UXGB",
        mac="dd",
        ip="",
        type="uxg",
        lldp_info=[],
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
