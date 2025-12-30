from unifi_mermaid.mermaid import render_mermaid
from unifi_mermaid.topology import Device, Edge, classify_device_type, group_devices_by_type


def test_classify_gateway_type():
    device = Device(name="Gateway", model_name="", mac="aa", ip="", type="gateway", lldp_info=[])
    assert classify_device_type(device) == "gateway"


def test_group_devices_by_type_includes_ap():
    devices = [Device(name="AP One", model_name="", mac="aa", ip="", type="uap", lldp_info=[])]
    groups = group_devices_by_type(devices)
    assert groups["ap"] == ["AP One"]


def test_render_mermaid_with_groups_uses_subgraph():
    edges = [Edge("Gateway", "Switch")]
    groups = {"gateway": ["Gateway"], "switch": ["Switch"], "ap": [], "other": []}
    output = render_mermaid(edges, groups=groups, group_order=["gateway", "switch", "ap", "other"])
    assert 'subgraph group_gateway["Gateway"]' in output
