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
