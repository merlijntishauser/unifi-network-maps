from unifi_mermaid.topology import LLDPEntry, build_edges


class DummyDevice:
    def __init__(self, name, mac, lldp_info):
        self.name = name
        self.mac = mac
        self.lldp_info = lldp_info
        self.model_name = ""
        self.ip = ""
        self.type = ""


def test_build_edges_deduplicates_links():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:02", "1")])
    dev_b = DummyDevice("Switch B", "aa:bb:cc:dd:ee:02", [LLDPEntry("aa:bb:cc:dd:ee:01", "2")])
    edges = build_edges([dev_a, dev_b])
    assert len(edges) == 1


def test_build_edges_includes_ports():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:02", "1")])
    dev_b = DummyDevice("Switch B", "aa:bb:cc:dd:ee:02", [LLDPEntry("aa:bb:cc:dd:ee:01", "2")])
    edges = build_edges([dev_a, dev_b], include_ports=True)
    assert edges[0].label == "Switch A: 1 <-> Switch B: 2"


def test_build_edges_only_unifi_filters_unknown_neighbors():
    dev_a = DummyDevice("Switch A", "aa:bb:cc:dd:ee:01", [LLDPEntry("aa:bb:cc:dd:ee:ff", "1")])
    edges = build_edges([dev_a], only_unifi=True)
    assert edges == []
