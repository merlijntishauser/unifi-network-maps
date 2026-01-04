import pytest

from unifi_network_maps.model.lldp import LLDPEntry, coerce_lldp, local_port_label


def test_coerce_lldp_requires_chassis_id():
    class Entry:
        port_id = "1"

    with pytest.raises(ValueError):
        coerce_lldp(Entry())


def test_local_port_label_uses_desc_when_no_number():
    entry = LLDPEntry(chassis_id="aa", port_id="aa:bb:cc:dd:ee:ff", port_desc="uplink")
    assert local_port_label(entry) == "uplink"


def test_local_port_label_ignores_mac_port_desc():
    entry = LLDPEntry(chassis_id="aa", port_id="eth1", port_desc="aa:bb:cc:dd:ee:ff")
    assert local_port_label(entry) == "Port 1"
