from unifi_network_maps.model.vlans import build_vlan_info


def _vlan_map(entries: list[dict[str, object]]) -> dict[int, dict[str, object]]:
    mapped: dict[int, dict[str, object]] = {}
    for entry in entries:
        vlan_id = entry.get("id")
        if isinstance(vlan_id, int):
            mapped[vlan_id] = entry
    return mapped


def test_build_vlan_info_includes_networks_and_clients():
    networks = [
        {"name": "LAN", "vlan_enabled": False},
        {"name": "Guest", "vlan": 20, "vlan_enabled": True},
    ]
    clients = [
        {"name": "Client A", "is_wired": True, "vlan": 20},
        {"name": "Client B", "is_wired": True, "vlan": 30},
    ]

    vlan_info = build_vlan_info(clients, networks)
    vlan_map = _vlan_map(vlan_info)

    assert vlan_map[1]["name"] == "LAN"
    assert vlan_map[1]["client_count"] == 0
    assert vlan_map[20]["name"] == "Guest"
    assert vlan_map[20]["client_count"] == 1
    assert vlan_map[30]["client_count"] == 1
