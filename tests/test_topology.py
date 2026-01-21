from types import SimpleNamespace

import pytest

from unifi_network_maps.model.topology import (
    Device,
    Edge,
    LLDPEntry,
    PortInfo,
    UplinkInfo,
    _aggregation_group,
    _as_bool,
    _as_float,
    _as_group_id,
    _as_int,
    _as_list,
    _client_channel,
    _client_display_name,
    _client_field,
    _client_unifi_flag,
    _client_uplink_mac,
    _client_uplink_port,
    _parse_uplink,
    _poe_ports_from_device,
    _port_speed_by_idx,
    _resolve_port_idx_from_lldp,
    _tree_edges_from_parent,
    _uplink_info,
    _uplink_name,
    build_client_edges,
    build_client_port_map,
    build_edges,
    build_node_type_map,
    build_topology,
    build_tree_edges_by_topology,
    classify_device_type,
    coerce_device,
    normalize_devices,
)


class DummyDevice:
    def __init__(self, name, mac, lldp_info, port_table=None):
        self.name = name
        self.mac = mac
        self.lldp_info = lldp_info
        self.port_table = port_table or []
        self.model_name = ""
        self.ip = ""
        self.type = ""


def test_build_edges_deduplicates_links():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:02", "1")])
    dev_b = DummyDevice("Switch B", "aa:bb:cc:dd:ee:02", [LLDPEntry("aa:bb:cc:dd:ee:01", "2")])
    edges = build_edges(normalize_devices([dev_a, dev_b]))
    assert len(edges) == 1


def test_build_edges_orders_deterministically():
    dev_a = DummyDevice(
        "Switch Z",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "2")],
    )
    dev_b = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [LLDPEntry("aa:bb:cc:dd:ee:02", "1")],
    )
    edges = build_edges(normalize_devices([dev_a, dev_b]))
    assert [(edge.left, edge.right) for edge in edges] == [("Switch A", "Switch Z")]


def test_build_edges_includes_ports():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:02", "1")])
    dev_b = DummyDevice("Switch B", "aa:bb:cc:dd:ee:02", [LLDPEntry("aa:bb:cc:dd:ee:01", "2")])
    edges = build_edges(normalize_devices([dev_a, dev_b]), include_ports=True)
    assert edges[0].label == "Switch A: 1 <-> Switch B: 2"


def test_build_edges_only_unifi_filters_unknown_neighbors():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:ff", "1")])
    edges = build_edges(normalize_devices([dev_a]), only_unifi=True)
    assert edges == []


def test_build_edges_includes_unknown_neighbors_when_allowed():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:ff", "1")])
    edges = build_edges(normalize_devices([dev_a]), only_unifi=False)
    assert edges[0].right == "aa:bb:cc:dd:ee:ff"


def test_build_edges_hides_mac_port_id():
    dev_switch = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [LLDPEntry("aa:bb:cc:dd:ee:02", "eth0", local_port_name="Port 2")],
    )
    dev_ap = DummyDevice(
        "AP One",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "78:45:58:9F:18:38")],
    )
    edges = build_edges(normalize_devices([dev_switch, dev_ap]), include_ports=True)
    assert edges[0].label == "Switch A: Port 2 <-> AP One: ?"


def test_build_edges_port_desc_includes_number_and_name():
    dev_switch = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [
            LLDPEntry(
                "aa:bb:cc:dd:ee:02",
                "eth1",
                port_desc="uplink fiberdream",
                local_port_idx=1,
            )
        ],
        port_table=[{"port_idx": 1, "poe_enable": True}],
    )
    dev_ap = DummyDevice(
        "AP One",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "eth0")],
    )
    edges = build_edges(normalize_devices([dev_switch, dev_ap]), include_ports=True)
    assert edges[0].label == "Switch A: Port 1 (uplink fiberdream) <-> AP One: Port 0"


def test_build_edges_sets_poe_when_active():
    dev_switch = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [LLDPEntry("aa:bb:cc:dd:ee:02", "eth1", local_port_idx=1)],
        port_table=[{"port_idx": 1, "poe_enable": True}],
    )
    dev_ap = DummyDevice(
        "AP One",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "eth0")],
    )
    edges = build_edges(normalize_devices([dev_switch, dev_ap]))
    assert edges[0].poe is True


def test_build_edges_sets_poe_with_power():
    dev_switch = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [LLDPEntry("aa:bb:cc:dd:ee:02", "eth1", local_port_idx=1)],
        port_table=[{"port_idx": 1, "poe_power": "7.01"}],
    )
    dev_ap = DummyDevice(
        "AP One",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "eth0")],
    )
    edges = build_edges(normalize_devices([dev_switch, dev_ap]))
    assert edges[0].poe is True


def test_build_edges_sets_poe_with_poe_good():
    dev_switch = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [LLDPEntry("aa:bb:cc:dd:ee:02", "eth1", local_port_idx=1)],
        port_table=[{"port_idx": 1, "poe_good": True}],
    )
    dev_ap = DummyDevice(
        "AP One",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "eth0")],
    )
    edges = build_edges(normalize_devices([dev_switch, dev_ap]))
    assert edges[0].poe is True


def test_build_edges_sets_poe_with_port_poe():
    dev_switch = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [LLDPEntry("aa:bb:cc:dd:ee:02", "eth1", local_port_idx=1)],
        port_table=[{"port_idx": 1, "port_poe": True}],
    )
    dev_ap = DummyDevice(
        "AP One",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "eth0")],
    )
    edges = build_edges(normalize_devices([dev_switch, dev_ap]))
    assert edges[0].poe is True


def test_build_edges_sets_speed_from_port():
    dev_switch = DummyDevice(
        "Switch A",
        "aa:bb:cc:dd:ee:01",
        [LLDPEntry("aa:bb:cc:dd:ee:02", "eth1", local_port_idx=1)],
        port_table=[{"port_idx": 1, "speed": 1000}],
    )
    dev_ap = DummyDevice(
        "AP One",
        "aa:bb:cc:dd:ee:02",
        [LLDPEntry("aa:bb:cc:dd:ee:01", "eth0")],
    )
    edges = build_edges(normalize_devices([dev_switch, dev_ap]))
    assert edges[0].speed == 1000


def test_coerce_device_uses_lldp_fallback():
    class DeviceWithLldp:
        name = "Device"
        model_name = ""
        mac = "aa"
        ip = ""
        type = ""
        lldp_info = None
        lldp = [LLDPEntry("bb", "1")]
        port_table = []

    device = coerce_device(DeviceWithLldp())
    assert device.lldp_info[0].chassis_id == "bb"


def test_coerce_device_uses_lldp_table_fallback():
    class DeviceWithLldpTable:
        name = "Device"
        model_name = ""
        mac = "aa"
        ip = ""
        type = ""
        lldp_info = None
        lldp = None
        lldp_table = [LLDPEntry("bb", "1")]
        port_table = []

    device = coerce_device(DeviceWithLldpTable())
    assert device.lldp_info[0].chassis_id == "bb"


def test_coerce_device_requires_name():
    class MissingName:
        name = ""
        model_name = ""
        mac = "aa"
        ip = ""
        type = ""
        lldp_info = [LLDPEntry("bb", "1")]
        port_table = []

    with pytest.raises(ValueError):
        coerce_device(MissingName())


def test_coerce_device_requires_lldp():
    class MissingLldp:
        name = "Device"
        model_name = ""
        mac = "aa"
        ip = ""
        type = ""
        lldp_info = None
        lldp = None
        port_table = []

    with pytest.raises(ValueError):
        coerce_device(MissingLldp())


@pytest.fixture()
def device_with_uplink_no_lldp():
    class MissingLldpWithUplink:
        name = "Device"
        model_name = ""
        mac = "aa"
        ip = ""
        type = ""
        lldp_info = None
        lldp = None
        uplink = {"uplink_mac": "bb", "uplink_device_name": "Gateway", "uplink_remote_port": 1}
        port_table = []

    return MissingLldpWithUplink()


def test_coerce_device_allows_uplink_when_lldp_missing(device_with_uplink_no_lldp):
    device = coerce_device(device_with_uplink_no_lldp)
    assert device.lldp_info == []


def test_build_edges_uses_uplink_fallback_fixture(device_with_uplink_no_lldp):
    gateway = Device(
        name="Gateway",
        model_name="",
        model="",
        mac="bb",
        ip="",
        type="gateway",
        lldp_info=[],
    )
    device = coerce_device(device_with_uplink_no_lldp)
    edges = build_edges([gateway, device], include_ports=True)
    assert edges[0].label == "Gateway: Port 1 <-> Device: ?"


def test_coerce_device_tracks_poe_false_when_power_invalid():
    class DeviceWithPort:
        name = "Device"
        model_name = ""
        mac = "aa"
        ip = ""
        type = ""
        lldp_info = [LLDPEntry("bb", "1")]
        port_table = [{"port_idx": 1, "poe_power": "bad"}]

    device = coerce_device(DeviceWithPort())
    assert device.poe_ports[1] is False


def test_build_tree_edges_returns_empty_without_gateways():
    edges = build_tree_edges_by_topology([Edge("A", "B")], gateways=[])
    assert edges == []


def test_coerce_device_missing_name_raises():
    device = SimpleNamespace(name=None, mac="aa", lldp_info=[])
    with pytest.raises(ValueError):
        coerce_device(device)


def test_coerce_device_missing_lldp_raises():
    device = SimpleNamespace(name="Dev", mac="aa", lldp_info=None, lldp=None)
    with pytest.raises(ValueError):
        coerce_device(device)


def test_build_edges_uses_uplink_fallback():
    gateway = Device(
        name="Gateway",
        model_name="",
        model="",
        mac="aa",
        ip="",
        type="gateway",
        lldp_info=[],
        poe_ports={1: True},
    )
    switch = Device(
        name="Switch",
        model_name="",
        model="",
        mac="bb",
        ip="",
        type="switch",
        lldp_info=[],
        uplink=UplinkInfo(mac="aa", name="Gateway", port=1),
    )
    edges = build_edges([gateway, switch], include_ports=True)
    assert edges[0].label == "Gateway: Port 1 <-> Switch: ?"


def test_poe_ports_from_device_skips_missing_port_idx():
    device = SimpleNamespace(port_table=[{"poe_enable": True}])
    assert _poe_ports_from_device(device) == {}


def test_poe_ports_from_device_reads_dict_power():
    device = SimpleNamespace(port_table=[{"port_idx": 2, "poe_power": "1.2"}])
    assert _poe_ports_from_device(device) == {2: True}


def test_poe_ports_from_device_reads_portidx_key():
    device = SimpleNamespace(port_table=[{"portIdx": 3, "poe_enable": True}])
    assert _poe_ports_from_device(device) == {3: True}


def test_as_group_id_handles_types():
    assert _as_group_id(None) is None
    assert _as_group_id(True) is None
    assert _as_group_id(5) == "5"
    assert _as_group_id(" lag1 ") == "lag1"
    assert _as_group_id(" ") is None
    assert _as_group_id(object()) is None


def test_aggregation_group_reads_dict_key():
    entry = {"lag_id": "lag5"}
    assert _aggregation_group(entry) == "lag5"


def test_aggregation_group_handles_missing_keys():
    entry = {"aggregation_group": None}
    assert _aggregation_group(entry) is None


def test_aggregation_group_reads_object_attr():
    class PortEntry:
        aggregation_group = None
        agg_id = "agg2"

    assert _aggregation_group(PortEntry()) == "agg2"


def test_client_uplink_mac_nested():
    client = {"uplink": {"uplink_mac": "aa:bb"}}
    assert _client_uplink_mac(client) == "aa:bb"


def test_client_uplink_port_nested_str():
    client = {"uplink": {"uplink_remote_port": "3"}}
    assert _client_uplink_port(client) == 3


def test_build_client_edges_skips_unwired():
    client = {"name": "Client", "is_wired": False, "sw_mac": "aa"}
    assert build_client_edges([client], {"aa": "Switch"}) == []


def test_build_edges_only_unifi_false_uses_chassis_id():
    lldp = SimpleNamespace(chassis_id="bb", local_port_idx=None, port_id="Port 1", port_desc=None)
    device = SimpleNamespace(
        name="Switch",
        model_name="",
        model="",
        mac="aa",
        ip="",
        type="switch",
        lldp_info=[lldp],
        port_table=[],
    )
    edges = build_edges([coerce_device(device)], only_unifi=False)
    assert edges[0].right == "bb"


def test_build_edges_only_unifi_skips_unknown_uplink():
    device = SimpleNamespace(
        name="Switch",
        model_name="",
        model="",
        mac="aa",
        ip="",
        type="switch",
        lldp_info=[],
        port_table=[],
        uplink_mac="cc",
    )
    edges = build_edges([coerce_device(device)], only_unifi=True)
    assert edges == []


def test_build_edges_only_unifi_false_includes_unknown_uplink():
    device = SimpleNamespace(
        name="Switch",
        model_name="",
        model="",
        mac="aa",
        ip="",
        type="switch",
        lldp_info=[],
        port_table=[],
        uplink_mac="cc",
    )
    edges = build_edges([coerce_device(device)], only_unifi=False)
    assert (edges[0].left, edges[0].right) == ("cc", "Switch")


def test_build_edges_resolves_port_idx_from_ifname():
    lldp = SimpleNamespace(
        chassis_id="bb",
        local_port_idx=None,
        local_port_name="eth1",
        port_id="Port 1",
        port_desc=None,
    )
    device = SimpleNamespace(
        name="Switch A",
        model_name="",
        model="",
        mac="aa",
        ip="",
        type="switch",
        lldp_info=[lldp],
        port_table=[{"port_idx": 2, "ifname": "eth1", "poe_enable": True}],
    )
    neighbor = SimpleNamespace(
        name="Switch B",
        model_name="",
        model="",
        mac="bb",
        ip="",
        type="switch",
        lldp_info=[],
        port_table=[],
    )
    edges = build_edges([coerce_device(device), coerce_device(neighbor)], include_ports=True)
    assert edges[0].label == "Switch A: Port 2 <-> Switch B: ?"


def test_build_tree_edges_no_gateways():
    assert build_tree_edges_by_topology([], []) == []


def test_as_bool_int_true():
    assert _as_bool(1) is True


def test_as_bool_str_truthy():
    assert _as_bool("yes") is True


def test_as_float_none_returns_zero():
    assert _as_float(None) == 0.0


def test_as_float_invalid_str_returns_zero():
    assert _as_float("nope") == 0.0


def test_as_float_int_returns_float():
    assert _as_float(2) == 2.0


def test_as_float_unknown_type_returns_zero():
    assert _as_float([]) == 0.0


def test_client_field_attribute_fallback():
    client = SimpleNamespace(name="Client")
    assert _client_field(client, "name") == "Client"


def test_client_display_name_missing_returns_none():
    client = {"name": " ", "hostname": "", "mac": ""}
    assert _client_display_name(client) is None


def test_client_uplink_port_direct_int():
    client = {"uplink_remote_port": 4}
    assert _client_uplink_port(client) == 4


def test_client_uplink_port_direct_str_digit():
    client = {"sw_port": "7"}
    assert _client_uplink_port(client) == 7


def test_client_uplink_port_parses_port_label():
    client = {"uplink_remote_port": "Port 9"}
    assert _client_uplink_port(client) == 9


def test_client_uplink_port_nested_int():
    client = {"uplink": {"uplink_remote_port": 8}}
    assert _client_uplink_port(client) == 8


def test_client_uplink_mac_nested_empty():
    client = {"uplink": {"uplink_mac": ""}}
    assert _client_uplink_mac(client) is None


def test_build_client_edges_include_ports_without_port():
    client = {"name": "Client", "is_wired": True, "sw_mac": "aa"}
    edges = build_client_edges([client], {"aa": "Switch"}, include_ports=True)
    assert edges[0].label is None


def test_build_node_type_map_skips_unwired_clients():
    client = {"name": "Client", "is_wired": False}
    assert "Client" not in build_node_type_map([], [client])


def test_build_client_edges_missing_name_or_uplink():
    client = {"name": "", "is_wired": True}
    assert build_client_edges([client], {"aa": "Switch"}) == []


def test_build_tree_edges_gateway_not_in_adjacency():
    assert build_tree_edges_by_topology([Edge("A", "B")], ["Missing"]) == []


def test_build_client_edges_dedupes():
    clients = [
        {"name": "Client", "is_wired": True, "sw_mac": "aa"},
        {"name": "Client", "is_wired": True, "sw_mac": "aa"},
    ]
    edges = build_client_edges(clients, {"aa": "Switch"})
    assert len(edges) == 1


def test_build_node_type_map_adds_wired_client():
    client = {"name": "Client", "is_wired": True}
    node_types = build_node_type_map([], [client])
    assert node_types["Client"] == "client"


def test_classify_device_type_other():
    device = SimpleNamespace(type="camera")
    assert classify_device_type(device) == "other"


def test_build_topology_returns_edges():
    lldp = SimpleNamespace(chassis_id="bb", local_port_idx=None, port_id="Port 1", port_desc=None)
    device = SimpleNamespace(
        name="Switch",
        model_name="",
        model="",
        mac="aa",
        ip="",
        type="switch",
        lldp_info=[lldp],
        port_table=[],
    )
    result = build_topology(
        [coerce_device(device)], include_ports=False, only_unifi=False, gateways=[]
    )
    assert result.raw_edges


def test_as_list_coerces_iterable():
    assert _as_list(("a", "b")) == ["a", "b"]


def test_as_int_parses_digit_string():
    assert _as_int("7") == 7


def test_client_unifi_flag_reads_int():
    client = {"is_unifi": 1}
    assert _client_unifi_flag(client) is True


def test_client_channel_reads_string():
    client = {"wifi_channel": "36"}
    assert _client_channel(client) == 36


def test_resolve_port_idx_matches_port_name():
    lldp = LLDPEntry(chassis_id="bb", port_id="Port 3", local_port_name="Port 3")
    port_table = [
        PortInfo(
            port_idx=3,
            name="Port 3",
            ifname=None,
            speed=None,
            aggregation_group=None,
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=None,
        )
    ]
    assert _resolve_port_idx_from_lldp(lldp, port_table) == 3


def test_resolve_port_idx_matches_port_number():
    lldp = LLDPEntry(chassis_id="bb", port_id="Port 9", local_port_name="Port 9")
    port_table = [
        PortInfo(
            port_idx=9,
            name="Uplink",
            ifname=None,
            speed=None,
            aggregation_group=None,
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=None,
        )
    ]
    assert _resolve_port_idx_from_lldp(lldp, port_table) == 9


def test_parse_uplink_reads_object_fields():
    uplink = SimpleNamespace(uplink_device_mac="aa", uplink_device_name="Core", port_idx=3)
    parsed = _parse_uplink(uplink)
    assert parsed == UplinkInfo(mac="aa", name="Core", port=3)


def test_uplink_info_falls_back_to_last_uplink_mac():
    device = SimpleNamespace(
        name="Switch",
        model_name="",
        model="",
        mac="aa",
        ip="",
        type="switch",
        lldp_info=[],
        port_table=[],
        last_uplink_mac="bb",
    )
    uplink, last_uplink = _uplink_info(device)
    assert uplink is None
    assert last_uplink == UplinkInfo(mac="bb", name=None, port=None)


def test_uplink_name_prefers_name_over_mac():
    uplink = UplinkInfo(mac="aa", name="Core Switch", port=None)
    assert _uplink_name(uplink, {}, only_unifi=True) == "Core Switch"


def test_tree_edges_from_parent_missing_original():
    parent = {"Switch A": "Gateway"}
    edges = _tree_edges_from_parent(parent, {})
    assert edges == [Edge(left="Gateway", right="Switch A")]


def test_build_client_port_map_skips_unknown_device():
    devices = [
        Device(name="Switch", model_name="", model="", mac="aa", ip="", type="usw", lldp_info=[])
    ]
    clients = [{"name": "Client", "is_wired": True, "sw_mac": "cc", "sw_port": 3}]
    assert build_client_port_map(devices, clients, client_mode="wired") == {}


def test_port_speed_by_idx_reads_speed():
    ports = [
        PortInfo(
            port_idx=1,
            name=None,
            ifname=None,
            speed=1000,
            aggregation_group=None,
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=None,
        )
    ]
    assert _port_speed_by_idx(ports, 1) == 1000


def test_classify_device_type_from_name():
    device = SimpleNamespace(type="", name="Gateway Main")
    assert classify_device_type(device) == "gateway"
