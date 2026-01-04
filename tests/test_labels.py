from unifi_network_maps.model.labels import compose_port_label, order_edge_names


def test_compose_port_label_with_both_sides():
    label = compose_port_label("A", "B", {("A", "B"): "Port 1", ("B", "A"): "Port 2"})
    assert label == "A: Port 1 <-> B: Port 2"


def test_compose_port_label_with_left_only():
    label = compose_port_label("A", "B", {("A", "B"): "Port 1"})
    assert label == "A: Port 1 <-> B: ?"


def test_compose_port_label_with_right_only():
    label = compose_port_label("A", "B", {("B", "A"): "Port 2"})
    assert label == "A: ? <-> B: Port 2"


def test_compose_port_label_with_none():
    label = compose_port_label("A", "B", {})
    assert label is None


def test_order_edge_names_swaps_when_right_label_only():
    ordered = order_edge_names("A", "B", {("B", "A"): "Port 2"}, lambda _name: 0)
    assert ordered == ("B", "A")


def test_order_edge_names_prefers_lower_rank():
    ordered = order_edge_names(
        "Switch",
        "Gateway",
        {("Switch", "Gateway"): "Port 1", ("Gateway", "Switch"): "Port 2"},
        lambda name: 1 if name == "Switch" else 0,
    )
    assert ordered == ("Gateway", "Switch")
