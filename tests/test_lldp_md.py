from unifi_network_maps.model.lldp import LLDPEntry
from unifi_network_maps.model.topology import Device, PortInfo, UplinkInfo
from unifi_network_maps.render import lldp_md
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


def test_render_lldp_md_only_unifi_filters_clients():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [
        {"name": "Desk PC", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 1},
        {
            "name": "Protect Cam",
            "is_wired": True,
            "sw_mac": "aa:bb",
            "sw_port": 2,
            "is_unifi": True,
        },
    ]
    output = render_lldp_md(
        devices,
        clients=clients,
        include_ports=True,
        show_clients=True,
        client_mode="wired",
        only_unifi=True,
    )
    assert "| Protect Cam | Port 2 |" in output
    assert "Desk PC" not in output


def test_render_lldp_md_uses_ucore_name_for_clients():
    devices = [
        Device(
            name="Switch A", model_name="", model="", mac="aa:bb", ip="", type="usw", lldp_info=[]
        )
    ]
    clients = [
        {
            "hostname": "espressif",
            "is_wired": True,
            "sw_mac": "aa:bb",
            "sw_port": 4,
            "unifi_device_info_from_ucore": {"name": "Smart PoE Chime"},
        }
    ]
    output = render_lldp_md(
        devices,
        clients=clients,
        include_ports=True,
        show_clients=True,
        client_mode="wired",
        only_unifi=True,
    )
    assert "| Smart PoE Chime | Port 4 |" in output
    assert "espressif" not in output


def test_client_display_name_falls_back_to_hostname():
    client = {"name": " ", "hostname": "Phone"}
    assert lldp_md._client_display_name(client) == "Phone"


def test_client_display_name_falls_back_to_mac():
    client = {"name": "", "hostname": "", "mac": "aa:bb"}
    assert lldp_md._client_display_name(client) == "aa:bb"


def test_client_uplink_mac_reads_nested():
    client = {"uplink": {"uplink_device_mac": "aa:bb"}}
    assert lldp_md._client_uplink_mac(client) == "aa:bb"


def test_client_uplink_port_parses_port_label():
    client = {"uplink_remote_port": "Port 9"}
    assert lldp_md._client_uplink_port(client) == 9


def test_client_unifi_flag_reads_int():
    client = {"is_unifi": 1}
    assert lldp_md._client_unifi_flag(client) is True


def test_client_is_unifi_uses_vendor():
    client = {"vendor": "Ubiquiti Networks"}
    assert lldp_md._client_is_unifi(client) is True


def test_client_ucore_display_name_uses_product_shortname():
    client = {"unifi_device_info_from_ucore": {"product_shortname": "UP Chime PoE"}}
    assert lldp_md._client_ucore_display_name(client) == "UP Chime PoE"


def test_uplink_summary_formats_port():
    device = Device(
        name="Switch A",
        model_name="",
        model="",
        mac="aa:bb",
        ip="",
        type="usw",
        lldp_info=[],
        uplink=UplinkInfo(mac=None, name="Core", port=3),
    )
    assert lldp_md._uplink_summary(device) == "Core (Port 3)"


def test_client_summary_truncates_samples():
    device = Device(
        name="Switch A",
        model_name="",
        model="",
        mac="aa:bb",
        ip="",
        type="usw",
        lldp_info=[],
    )
    rows = {"Switch A": [("A", None), ("B", "Port 1"), ("C", None), ("D", "Port 2")]}
    count, sample = lldp_md._client_summary(device, rows)
    assert count == "4"
    assert sample == "A, B, C, ..."


def test_client_rows_filters_only_unifi_and_includes_ports():
    device_index = {"aa:bb": "Switch A"}
    clients = [
        {"name": "TV", "is_wired": True, "sw_mac": "aa:bb", "sw_port": 1, "vendor": "LG"},
        {
            "name": "Camera",
            "is_wired": True,
            "sw_mac": "aa:bb",
            "sw_port": 2,
            "vendor": "Ubiquiti",
        },
    ]
    rows = lldp_md._client_rows(
        clients,
        device_index,
        include_ports=True,
        client_mode="wired",
        only_unifi=True,
    )
    assert rows["Switch A"] == [("Camera", "Port 2")]


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


def test_render_lldp_md_escapes_markdown_specials():
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
                    port_desc="Bad[link]*_`<script>`",
                )
            ],
        ),
    ]
    output = render_lldp_md(devices)
    assert r"Bad\[link\]\*\_\`\<script\>\`" in output


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
