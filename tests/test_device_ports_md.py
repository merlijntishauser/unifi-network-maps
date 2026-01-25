from unifi_network_maps.model.topology import Device, PortInfo, UplinkInfo
from unifi_network_maps.render.device_ports_md import render_device_port_overview


def _device_with_ports(name, *, dev_type="usw", ports=None, uplink=None, model_name="", model=""):
    return Device(
        name=name,
        model_name=model_name,
        model=model_name,
        mac="aa:bb",
        ip="192.168.1.2",
        type=dev_type,
        lldp_info=[],
        port_table=ports or [],
        poe_ports={},
        uplink=uplink,
        last_uplink=None,
        version="1.2.3",
    )


def test_gateway_uplink_unknown_renders_internet():
    device = _device_with_ports(
        "Gateway",
        dev_type="udm",
        uplink=UplinkInfo(mac=None, name=None, port=5),
    )
    output = render_device_port_overview([device], {})
    assert "Internet (Port 5)" in output


def test_port_speed_formats_2500_as_2_5g():
    port = PortInfo(
        port_idx=1,
        name="Port 1",
        ifname="eth1",
        speed=2500,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "2.5G" in output


def test_poe_disabled_is_not_active():
    port = PortInfo(
        port_idx=2,
        name="Port 2",
        ifname="eth2",
        speed=1000,
        aggregation_group=None,
        port_poe=True,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| disabled |" in output


def test_aggregated_ports_are_combined():
    ports = [
        PortInfo(
            port_idx=5,
            name="Port 5",
            ifname="eth5",
            speed=1000,
            aggregation_group=None,
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
        PortInfo(
            port_idx=6,
            name="Port 6 (LAG)",
            ifname="eth6",
            speed=1000,
            aggregation_group="lag1",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "Port 5-6 (LAG)" in output


def test_multiple_clients_render_as_list():
    port = PortInfo(
        port_idx=4,
        name="Port 4",
        ifname="eth4",
        speed=100,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    client_ports = {"Switch": [(4, "Client A"), (4, "Client B")]}
    output = render_device_port_overview([device], {}, client_ports=client_ports)
    assert 'class="unifi-port-clients"' in output


def test_custom_port_name_only():
    port = PortInfo(
        port_idx=3,
        name="Port 3 - Hue Bridge",
        ifname="eth3",
        speed=100,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "Port 3 - Hue Bridge" in output


def test_client_list_renders_as_html_list():
    port = PortInfo(
        port_idx=9,
        name="Port 9",
        ifname="eth9",
        speed=1000,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    client_ports = {"Switch": [(9, "Client A"), (9, "Client B")]}
    output = render_device_port_overview([device], {}, client_ports=client_ports)
    assert "<ul" in output and "<li>Client A</li>" in output


def test_single_client_uses_inline_label():
    port = PortInfo(
        port_idx=10,
        name="Port 10",
        ifname="eth10",
        speed=1000,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    client_ports = {"Switch": [(10, "Client Solo")]}
    output = render_device_port_overview([device], {}, client_ports=client_ports)
    assert "Client Solo (client)" in output


def test_single_client_escapes_markdown_specials():
    port = PortInfo(
        port_idx=13,
        name="Port 13",
        ifname="eth13",
        speed=1000,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    client_ports = {"Switch": [(13, "Bad[link]*_`<script>`")]}
    output = render_device_port_overview([device], {}, client_ports=client_ports)
    assert r"Bad\[link\]\*\_\`\<script\>\` (client)" in output


def test_speed_formats_megabit():
    port = PortInfo(
        port_idx=11,
        name="Port 11",
        ifname="eth11",
        speed=100,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| 100M |" in output


def test_peer_name_escapes_markdown_specials():
    port = PortInfo(
        port_idx=14,
        name="Port 14",
        ifname="eth14",
        speed=1000,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    port_map = {("Switch", "Peer[bad]"): "Port 14", ("Peer[bad]", "Switch"): "Port 1"}
    output = render_device_port_overview([device], port_map)
    assert r"Peer\[bad\] (Port 1)" in output


def test_poe_state_active_when_power_present():
    port = PortInfo(
        port_idx=12,
        name="Port 12",
        ifname="eth12",
        speed=1000,
        aggregation_group=None,
        port_poe=True,
        poe_enable=True,
        poe_good=False,
        poe_power=3.2,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| active |" in output


def test_aggregate_label_for_non_consecutive_ports():
    ports = [
        PortInfo(
            port_idx=2,
            name="Port 2 (LAG)",
            ifname="eth2",
            speed=1000,
            aggregation_group="lag2",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
        PortInfo(
            port_idx=4,
            name="Port 4 (LAG)",
            ifname="eth4",
            speed=1000,
            aggregation_group="lag2",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "Ports 2+4 (LAG)" in output


def test_model_falls_back_to_type_when_missing():
    device = _device_with_ports("Switch", model_name="")
    output = render_device_port_overview([device], {})
    assert "| Model | usw |" in output


def test_port_label_uses_name_when_no_index():
    port = PortInfo(
        port_idx=None,
        name="Mgmt",
        ifname="mgmt0",
        speed=None,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| Mgmt |" in output


def test_port_label_falls_back_to_unknown():
    port = PortInfo(
        port_idx=None,
        name=None,
        ifname="ethX",
        speed=None,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| Port ? |" in output


def test_port_label_ignores_default_name():
    port = PortInfo(
        port_idx=1,
        name="Port 1",
        ifname="eth1",
        speed=1000,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| Port 1 |" in output


def test_poe_state_capable_when_enabled_no_power():
    port = PortInfo(
        port_idx=13,
        name="Port 13",
        ifname="eth13",
        speed=1000,
        aggregation_group=None,
        port_poe=True,
        poe_enable=True,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| capable |" in output


def test_speed_unknown_renders_dash():
    port = PortInfo(
        port_idx=14,
        name="Port 14",
        ifname="eth14",
        speed=None,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    output = render_device_port_overview([device], {})
    assert "| - | - |" in output


def test_aggregate_speed_mixed():
    ports = [
        PortInfo(
            port_idx=1,
            name="Port 1 (LAG)",
            ifname="eth1",
            speed=1000,
            aggregation_group="lagX",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
        PortInfo(
            port_idx=2,
            name="Port 2 (LAG)",
            ifname="eth2",
            speed=2500,
            aggregation_group="lagX",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "| mixed |" in output


def test_aggregate_poe_state_disabled():
    ports = [
        PortInfo(
            port_idx=3,
            name="Port 3 (LAG)",
            ifname="eth3",
            speed=1000,
            aggregation_group="lagY",
            port_poe=True,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
        PortInfo(
            port_idx=4,
            name="Port 4 (LAG)",
            ifname="eth4",
            speed=1000,
            aggregation_group="lagY",
            port_poe=True,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "| disabled |" in output


def test_aggregate_power_total():
    ports = [
        PortInfo(
            port_idx=7,
            name="Port 7 (LAG)",
            ifname="eth7",
            speed=1000,
            aggregation_group="lagZ",
            port_poe=True,
            poe_enable=True,
            poe_good=True,
            poe_power=1.25,
        ),
        PortInfo(
            port_idx=8,
            name="Port 8 (LAG)",
            ifname="eth8",
            speed=1000,
            aggregation_group="lagZ",
            port_poe=True,
            poe_enable=True,
            poe_good=True,
            poe_power=2.5,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "3.75W" in output


def test_aggregate_label_single_port():
    ports = [
        PortInfo(
            port_idx=9,
            name="Port 9 (LAG)",
            ifname="eth9",
            speed=1000,
            aggregation_group="lag9",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "Port 9 (LAG)" in output


def test_aggregate_fallback_groups_adjacent():
    ports = [
        PortInfo(
            port_idx=8,
            name="Port 8",
            ifname="eth8",
            speed=1000,
            aggregation_group=None,
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
        PortInfo(
            port_idx=9,
            name="Port 9 (LAG)",
            ifname="eth9",
            speed=1000,
            aggregation_group=None,
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "Port 8-9 (LAG)" in output


def test_aggregate_label_without_port_idx():
    ports = [
        PortInfo(
            port_idx=None,
            name="LAG",
            ifname="lag0",
            speed=None,
            aggregation_group="lag0",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "Aggregated ports" in output


def test_aggregate_speed_dash_when_missing():
    ports = [
        PortInfo(
            port_idx=1,
            name="Port 1 (LAG)",
            ifname="eth1",
            speed=None,
            aggregation_group="lagM",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
        PortInfo(
            port_idx=2,
            name="Port 2 (LAG)",
            ifname="eth2",
            speed=None,
            aggregation_group="lagM",
            port_poe=False,
            poe_enable=False,
            poe_good=False,
            poe_power=0.0,
        ),
    ]
    device = _device_with_ports("Switch", ports=ports)
    output = render_device_port_overview([device], {})
    assert "| - |" in output


def test_peer_and_clients_render_with_break():
    port = PortInfo(
        port_idx=15,
        name="Port 15",
        ifname="eth15",
        speed=1000,
        aggregation_group=None,
        port_poe=False,
        poe_enable=False,
        poe_good=False,
        poe_power=0.0,
    )
    device = _device_with_ports("Switch", ports=[port])
    port_map = {("Switch", "AP"): "Port 15", ("AP", "Switch"): "Port 9"}
    client_ports = {"Switch": [(15, "Client A"), (15, "Client B")]}
    output = render_device_port_overview([device], port_map, client_ports=client_ports)
    assert "<br/>" in output and "AP (Port 9)" in output
