from unifi_network_maps.model.lldp import LLDPEntry
from unifi_network_maps.model.topology import Device
from unifi_network_maps.render.lldp_md import render_lldp_md


def test_render_lldp_md_includes_device_header():
    devices = [Device(name="Switch A", model_name="", mac="aa:bb", ip="", type="usw", lldp_info=[])]
    output = render_lldp_md(devices)
    assert "## Switch A" in output


def test_render_lldp_md_uses_neighbor_name_from_index():
    devices = [
        Device(
            name="Switch A",
            model_name="",
            mac="aa:bb",
            ip="",
            type="usw",
            lldp_info=[
                LLDPEntry(chassis_id="cc:dd", port_id="Port 2", local_port_idx=1),
            ],
        ),
        Device(name="Switch B", model_name="", mac="cc:dd", ip="", type="usw", lldp_info=[]),
    ]
    output = render_lldp_md(devices)
    assert "| Port 1 | Switch B | Port 2 | cc:dd | - |" in output


def test_render_lldp_md_reports_missing_neighbors():
    devices = [Device(name="AP One", model_name="", mac="aa:cc", ip="", type="uap", lldp_info=[])]
    output = render_lldp_md(devices)
    assert "_No LLDP neighbors._" in output


def test_render_lldp_md_includes_clients_when_requested():
    devices = [Device(name="Switch A", model_name="", mac="aa:bb", ip="", type="usw", lldp_info=[])]
    clients = [{"name": "TV", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 3}]
    output = render_lldp_md(devices, clients=clients, include_ports=True, show_clients=True)
    assert "| TV | Port 3 |" in output
