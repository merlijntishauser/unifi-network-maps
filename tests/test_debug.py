import logging
from types import SimpleNamespace

from unifi_network_maps.io.debug import debug_dump_devices, device_to_dict
from unifi_network_maps.model.topology import Device


def test_device_to_dict_prefers_to_dict():
    class WithToDict:
        def to_dict(self):
            return {"name": "value"}

    assert device_to_dict(WithToDict()) == {"name": "value"}


def test_device_to_dict_uses_dunder_dict():
    class WithDict:
        def __init__(self):
            self.value = 3

    assert device_to_dict(WithDict()) == {"value": 3}


def test_device_to_dict_falls_back_to_repr():
    class NoDict:
        __slots__ = ()

        def __repr__(self):
            return "noop"

    assert device_to_dict(NoDict()) == {"repr": "noop"}


def test_debug_dump_devices_logs_gateway_and_sample(caplog):
    raw = [
        SimpleNamespace(name="Gateway", data="gw"),
        SimpleNamespace(name="Switch", data="sw"),
    ]
    normalized = [
        Device(name="Gateway", model_name="", model="", mac="aa", ip="", type="udm", lldp_info=[]),
        Device(name="Switch", model_name="", model="", mac="bb", ip="", type="usw", lldp_info=[]),
    ]

    caplog.set_level(logging.INFO)
    debug_dump_devices(raw, normalized, sample_count=1)
    assert "Gateway" in caplog.text
