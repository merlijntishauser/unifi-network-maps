from unifi_mermaid.labels import compose_port_label


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
