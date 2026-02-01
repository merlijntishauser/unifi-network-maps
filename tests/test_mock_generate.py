import json

from unifi_network_maps.io.mock_generate import (
    MockOptions,
    generate_mock_payload,
    mock_payload_json,
)


def test_generate_mock_payload_counts():
    options = MockOptions(seed=123, switch_count=2, ap_count=3, wired_client_count=4)
    payload = generate_mock_payload(options)
    assert len(payload["devices"]) == 1 + 2 + 3
    assert len(payload["clients"]) == 4 + options.wireless_client_count


def test_generate_mock_payload_deterministic():
    options = MockOptions(seed=123, switch_count=2, ap_count=1, wired_client_count=1)
    payload_a = generate_mock_payload(options)
    payload_b = generate_mock_payload(options)
    assert payload_a == payload_b


def test_mock_payload_json_is_valid():
    options = MockOptions(seed=1)
    payload = json.loads(mock_payload_json(options))
    assert "devices" in payload
    assert "clients" in payload
    assert "networks" in payload
    assert "vlan_info" in payload
