from unifi_mermaid.topology import LLDPEntry, build_edges, normalize_devices


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


def test_build_edges_includes_ports():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:02", "1")])
    dev_b = DummyDevice("Switch B", "aa:bb:cc:dd:ee:02", [LLDPEntry("aa:bb:cc:dd:ee:01", "2")])
    edges = build_edges(normalize_devices([dev_a, dev_b]), include_ports=True)
    assert edges[0].label == "Switch A: 1 <-> Switch B: 2"


def test_build_edges_only_unifi_filters_unknown_neighbors():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:ff", "1")])
    edges = build_edges(normalize_devices([dev_a]), only_unifi=True)
    assert edges == []


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
