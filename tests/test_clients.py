from unifi_network_maps.model.topology import Device, build_client_edges, build_node_type_map


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


def test_build_client_edges_includes_wireless_when_requested():
    device_index = {"aa:bb:cc:dd:ee:ff": "AP One"}
    clients = [{"name": "Laptop", "ap_mac": "aa:bb:cc:dd:ee:ff", "is_wired": False}]
    edges = build_client_edges(clients, device_index, client_mode="wireless")
    assert edges[0].wireless is True


def test_build_client_edges_includes_channel_for_wireless():
    device_index = {"aa:bb:cc:dd:ee:ff": "AP One"}
    clients = [{"name": "Phone", "ap_mac": "aa:bb:cc:dd:ee:ff", "is_wired": False, "channel": 36}]
    edges = build_client_edges(clients, device_index, client_mode="wireless")
    assert edges[0].channel == 36


def test_build_client_edges_includes_uplink_port_label():
    device_index = {"aa:bb:cc:dd:ee:ff": "Switch A"}
    clients = [
        {
            "name": "Laptop",
            "sw_mac": "aa:bb:cc:dd:ee:ff",
            "is_wired": True,
            "last_uplink": {"uplink_remote_port": 3},
        }
    ]
    edges = build_client_edges(clients, device_index, include_ports=True)
    assert edges[0].label == "Switch A: Port 3 <-> Laptop"


def test_build_client_edges_only_unifi_filters_non_unifi():
    device_index = {"aa:bb:cc:dd:ee:ff": "Switch A"}
    clients = [
        {"name": "Desk PC", "is_wired": True, "sw_mac": "aa:bb:cc:dd:ee:ff", "is_unifi": False},
        {"name": "Protect Cam", "is_wired": True, "sw_mac": "aa:bb:cc:dd:ee:ff", "is_unifi": True},
    ]
    edges = build_client_edges(clients, device_index, only_unifi=True)
    assert [edge.right for edge in edges] == ["Protect Cam"]


def test_build_client_edges_only_unifi_vendor_fallback():
    device_index = {"aa:bb:cc:dd:ee:ff": "Switch A"}
    clients = [
        {
            "name": "UniFi Sensor",
            "is_wired": True,
            "sw_mac": "aa:bb:cc:dd:ee:ff",
            "oui": "Ubiquiti Inc.",
        }
    ]
    edges = build_client_edges(clients, device_index, only_unifi=True)
    assert edges[0].right == "UniFi Sensor"


def test_build_client_edges_only_unifi_ucore_managed():
    device_index = {"aa:bb:cc:dd:ee:ff": "Switch A"}
    clients = [
        {
            "name": "Doorbell Lite",
            "is_wired": True,
            "sw_mac": "aa:bb:cc:dd:ee:ff",
            "unifi_device_info_from_ucore": {"managed": True},
        }
    ]
    edges = build_client_edges(clients, device_index, only_unifi=True)
    assert edges[0].right == "Doorbell Lite"


def test_build_client_edges_prefers_ucore_name_over_hostname():
    device_index = {"aa:bb:cc:dd:ee:ff": "Switch A"}
    clients = [
        {
            "hostname": "espressif",
            "is_wired": True,
            "sw_mac": "aa:bb:cc:dd:ee:ff",
            "unifi_device_info_from_ucore": {"name": "Smart PoE Chime"},
        }
    ]
    edges = build_client_edges(clients, device_index, only_unifi=True)
    assert edges[0].right == "Smart PoE Chime"


def test_build_node_type_map_skips_wireless_clients():
    devices = [
        Device(name="Gateway", model_name="", model="", mac="aa", ip="", type="udm", lldp_info=[])
    ]
    clients = [{"name": "Phone", "is_wired": False}]
    node_types = build_node_type_map(devices, clients)
    assert "Phone" not in node_types


def test_build_node_type_map_only_unifi_filters_clients():
    devices = [
        Device(name="Gateway", model_name="", model="", mac="aa", ip="", type="udm", lldp_info=[])
    ]
    clients = [
        {"name": "Desk PC", "is_wired": True, "is_unifi": False},
        {"name": "Protect Cam", "is_wired": True, "is_unifi": True},
    ]
    node_types = build_node_type_map(devices, clients, only_unifi=True)
    assert "Protect Cam" in node_types
    assert "Desk PC" not in node_types
