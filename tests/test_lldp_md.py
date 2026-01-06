from unifi_network_maps.model.lldp import LLDPEntry
from unifi_network_maps.model.topology import Device, PortInfo
from unifi_network_maps.render.lldp_md import render_lldp_md


def test_render_lldp_md_includes_device_header():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    output = render_lldp_md(devices)
    assert "## Switch A" in output
    assert "### Details" in output
    assert "| PoE |" in output


def test_render_lldp_md_uses_neighbor_name_from_index():
    devices = [
        Device(
            name="Switch A",
            model_name="",
            model="",
            mac="aa:bb",
            ip="",
            type="usw",
            lldp_info=[
                LLDPEntry(chassis_id="cc:dd", port_id="Port 2", local_port_idx=1),
            ],
        ),
        Device(
            name="Switch B", model_name="", model="", mac="cc:dd", ip="", type="usw", lldp_info=[]
        ),
    ]
    output = render_lldp_md(devices)
    assert "| Port 1 | Switch B | Port 2 | cc:dd | - |" in output


def test_render_lldp_md_reports_missing_neighbors():
    devices = [
        Device(name="AP One", model_name="", model="", mac="aa:cc", ip="", type="uap", lldp_info=[])
    ]
    output = render_lldp_md(devices)
    assert "_No LLDP neighbors._" in output


def test_render_lldp_md_includes_ports_section_when_enabled():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    output = render_lldp_md(devices, include_ports=True)
    assert "### Ports" in output


def test_render_lldp_md_includes_clients_when_requested():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"name": "TV", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 3}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="wired"
    )
    assert "| TV | Port 3 |" in output


def test_render_lldp_md_includes_ports_only_when_enabled():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    output = render_lldp_md(devices, include_ports=False)
    assert "### Ports" not in output


def test_render_lldp_md_skips_client_section_when_disabled():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"name": "TV", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 3}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=False, client_mode="wired"
    )
    assert "### Clients" not in output


def test_render_lldp_md_includes_neighbor_port_desc():
    devices = [
        Device(
            name="Switch A",
            model_name="",
            model="",
            mac="aa:bb",
            ip="",
            type="usw",
            lldp_info=[
                LLDPEntry(
                    chassis_id="cc:dd",
                    port_id="Port 2",
                    local_port_idx=1,
                    port_desc="Uplink",
                )
            ],
        ),
        Device(
            name="Switch B", model_name="", model="", mac="cc:dd", ip="", type="usw", lldp_info=[]
        ),
    ]
    output = render_lldp_md(devices)
    assert "| Port 1 (Uplink) | Switch B | Port 2 | cc:dd | Uplink |" in output


def test_render_lldp_md_skips_client_rows_when_missing_uplink():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"name": "TV", "is_wired": True}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="wired"
    )
    assert "| TV |" not in output


def test_render_lldp_md_renders_client_list_when_no_ports():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"hostname": "TV", "is_wired": True, "sw_mac": "aa:bb"}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=False, show_clients=True, client_mode="wired"
    )
    assert "- TV" in output


def test_render_lldp_md_skips_wireless_in_wired_mode():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"hostname": "Phone", "is_wired": False, "sw_mac": "aa:bb"}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="wired"
    )
    assert "Phone" not in output


def test_render_lldp_md_escapes_pipe_in_port_desc():
    devices = [
        Device(
            name="Switch A",
            model_name="",
            model="",
            mac="aa:bb",
            ip="",
            type="usw",
            lldp_info=[
                LLDPEntry(
                    chassis_id="cc:dd", port_id="Port 2", local_port_idx=1, port_desc="Up|link"
                )
            ],
        ),
    ]
    output = render_lldp_md(devices)
    assert "Up\\|link" in output


def test_render_lldp_md_reads_client_from_object():
    class Client:
        hostname = "Console"
        is_wired = True
        sw_mac = "aa:bb"
        sw_port = 2

    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    output = render_lldp_md(
        devices, clients=[Client()], include_ports=True, show_clients=True, client_mode="wired"
    )
    assert "| Console | Port 2 |" in output


def test_render_lldp_md_client_uplink_from_nested():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"name": "TV", "uplink": {"uplink_device_mac": "aa:bb", "uplink_remote_port": "4"}}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="all"
    )
    assert "| TV | Port 4 |" in output


def test_render_lldp_md_all_client_mode():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [
        {"name": "Phone", "is_wired": False, "sw_mac": "aa:bb", "sw_port": 2},
        {"name": "TV", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 3},
    ]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="all"
    )
    assert "| Phone | Port 2 |" in output
    assert "| TV | Port 3 |" in output


def test_render_lldp_md_port_summary_includes_power():
    ports = [
        PortInfo(
            port_idx=1,
            name="Port 1",
            ifname="eth1",
            speed=1000,
            aggregation_group=None,
            port_poe=True,
            poe_enable=True,
            poe_good=True,
            poe_power=3.5,
        )
    ]
    devices = [
        Device(
            name="Switch A",
            model_name="",
            model="",
            mac="aa:bb",
            ip="",
            type="usw",
            lldp_info=[],
            port_table=ports,
        )
    ]
    output = render_lldp_md(devices)
    assert "W" in output


def test_render_lldp_md_escapes_pipe_in_client_name():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"name": "TV|Box", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 1}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="wired"
    )
    assert "TV\\|Box" in output


def test_render_lldp_md_escapes_pipe_in_port_label():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [{"name": "TV", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 1}]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="wired"
    )
    assert "| TV | Port 1 |" in output


def test_render_lldp_md_client_scope_wireless():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [
        {"name": "Phone", "is_wired": False, "sw_mac": "aa:bb", "sw_port": 2},
        {"name": "TV", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 3},
    ]
    output = render_lldp_md(
        devices, clients=clients, include_ports=True, show_clients=True, client_mode="wireless"
    )
    assert "Phone" in output
    assert "TV" not in output
