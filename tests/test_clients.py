from unifi_mermaid.topology import build_client_edges


def test_build_client_edges_maps_ap_mac():
    device_index = {"aa:bb:cc:dd:ee:ff": "AP One"}
    clients = [{"name": "Laptop", "ap_mac": "aa:bb:cc:dd:ee:ff", "is_wired": True}]
    edges = build_client_edges(clients, device_index)
    assert edges[0].left == "AP One"


def test_build_client_edges_uses_hostname_fallback():
    device_index = {"aa:bb:cc:dd:ee:ff": "Switch A"}
    clients = [{"hostname": "phone", "sw_mac": "aa:bb:cc:dd:ee:ff", "is_wired": True}]
    edges = build_client_edges(clients, device_index)
    assert edges[0].right == "phone"


def test_build_client_edges_skips_unknown_uplink():
    device_index = {"aa:bb:cc:dd:ee:ff": "Switch A"}
    clients = [{"name": "tablet", "sw_mac": "11:22:33:44:55:66", "is_wired": True}]
    edges = build_client_edges(clients, device_index)
    assert edges == []


def test_build_client_edges_skips_wireless_clients():
    device_index = {"aa:bb:cc:dd:ee:ff": "AP One"}
    clients = [{"name": "Laptop", "ap_mac": "aa:bb:cc:dd:ee:ff", "is_wired": False}]
    edges = build_client_edges(clients, device_index)
    assert edges == []
