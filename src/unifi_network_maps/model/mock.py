"""Generate mock UniFi data using Faker."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from faker import Faker

from .vlans import build_vlan_info, normalize_networks


@dataclass(frozen=True)
class MockOptions:
    seed: int = 1337
    switch_count: int = 1
    ap_count: int = 2
    wired_client_count: int = 2
    wireless_client_count: int = 2


@dataclass
class _MockState:
    fake: Faker
    rng: random.Random
    used_macs: set[str] = field(default_factory=set)
    used_ips: set[str] = field(default_factory=set)
    used_names: set[str] = field(default_factory=set)
    used_rooms: set[str] = field(default_factory=set)
    core_port_next: int = 2


def generate_mock_payload(options: MockOptions) -> dict[str, list[dict[str, Any]]]:
    state = _build_state(options.seed)
    devices, core_switch, aps = _build_devices(options, state)
    clients = _build_clients(options, state, core_switch, aps)
    networks = _build_networks()
    vlan_info = build_vlan_info(clients, networks)
    return {
        "devices": devices,
        "clients": clients,
        "networks": normalize_networks(networks),
        "vlan_info": vlan_info,
    }


def mock_payload_json(options: MockOptions) -> str:
    payload = generate_mock_payload(options)
    return json.dumps(payload, indent=2, sort_keys=True)


def _build_state(seed: int) -> _MockState:
    fake = Faker("en_US")
    fake.seed_instance(seed)
    rng = random.Random(seed)
    return _MockState(fake=fake, rng=rng)


def _build_devices(
    options: MockOptions, state: _MockState
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    gateway = _build_gateway(state)
    core_switch = _build_core_switch(state)
    _link_gateway_to_switch(state, gateway, core_switch)
    access_switches = _build_access_switches(options.switch_count - 1, state, core_switch)
    aps = _build_aps(options.ap_count, state, core_switch)
    devices = [gateway, core_switch] + access_switches + aps
    return devices, core_switch, aps


def _build_gateway(state: _MockState) -> dict[str, Any]:
    device = _device_base(state, "Cloud Gateway", "udm", "UniFi Dream Machine Pro", "UDM-Pro")
    _add_port(device, 9, poe_enabled=False, rng=state.rng)
    return device


def _build_core_switch(state: _MockState) -> dict[str, Any]:
    return _device_base(state, "Core Switch", "usw", "UniFi Switch 24 PoE", "USW-24-PoE")


def _build_access_switches(
    count: int, state: _MockState, core_switch: dict[str, Any]
) -> list[dict[str, Any]]:
    switches = []
    for _ in range(max(0, count)):
        room = _unique_room(state)
        name = _unique_name(state, f"Switch {room}")
        device = _device_base(state, name, "usw", "UniFi Switch Lite 8 PoE", "USW-Lite-8-PoE")
        _link_core_device(state, core_switch, device, poe_enabled=False)
        switches.append(device)
    return switches


def _build_aps(count: int, state: _MockState, core_switch: dict[str, Any]) -> list[dict[str, Any]]:
    aps = []
    for _ in range(max(0, count)):
        room = _unique_room(state)
        name = _unique_name(state, f"AP {room}")
        device = _device_base(state, name, "uap", "UniFi AP 6 Lite", "U6-Lite")
        _add_port(device, 1, poe_enabled=True, rng=state.rng)
        _link_core_device(state, core_switch, device, poe_enabled=True)
        aps.append(device)
    return aps


def _build_clients(
    options: MockOptions,
    state: _MockState,
    core_switch: dict[str, Any],
    aps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    clients = []
    clients.extend(_build_wired_clients(options.wired_client_count, state, core_switch))
    clients.extend(_build_wireless_clients(options.wireless_client_count, state, aps))
    return clients


def _build_networks() -> list[dict[str, Any]]:
    return [
        {"name": "LAN", "vlan_enabled": False, "purpose": "corporate"},
        {"name": "Guest", "vlan": 20, "vlan_enabled": True, "purpose": "guest"},
    ]


def _build_wired_clients(
    count: int, state: _MockState, core_switch: dict[str, Any]
) -> list[dict[str, Any]]:
    clients = []
    for _ in range(max(0, count)):
        port_idx = _next_core_port(state)
        _add_port(core_switch, port_idx, poe_enabled=False, rng=state.rng)
        name = _unique_client_name(state)
        clients.append(
            {
                "name": name,
                "is_wired": True,
                "sw_mac": core_switch["mac"],
                "sw_port": port_idx,
            }
        )
    return clients


def _build_wireless_clients(
    count: int, state: _MockState, aps: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not aps:
        return []
    clients = []
    for idx in range(max(0, count)):
        ap = aps[idx % len(aps)]
        name = _unique_client_name(state)
        clients.append(
            {
                "name": name,
                "is_wired": False,
                "ap_mac": ap["mac"],
                "ap_port": 1,
            }
        )
    return clients


def _device_base(
    state: _MockState, name: str, dev_type: str, model_name: str, model: str
) -> dict[str, Any]:
    version = _pick_version(state, dev_type)
    return {
        "name": name,
        "model_name": model_name,
        "model": model,
        "mac": _unique_mac(state),
        "ip": _unique_ip(state),
        "type": dev_type,
        "version": version,
        "port_table": [],
        "lldp_info": [],
    }


def _pick_version(state: _MockState, dev_type: str) -> str:
    versions = {
        "udm": ["3.1.0", "3.1.1"],
        "usw": ["7.0.0", "7.1.2"],
        "uap": ["6.6.55", "6.7.10"],
    }
    return state.rng.choice(versions.get(dev_type, ["1.0.0"]))


def _link_gateway_to_switch(
    state: _MockState, gateway: dict[str, Any], core_switch: dict[str, Any]
) -> None:
    _add_port(core_switch, 1, poe_enabled=False, rng=state.rng)
    _add_lldp_link(
        gateway,
        core_switch,
        local_port=9,
        remote_port=1,
        remote_name=core_switch["name"],
    )
    _add_lldp_link(
        core_switch,
        gateway,
        local_port=1,
        remote_port=9,
        remote_name=gateway["name"],
    )


def _link_core_device(
    state: _MockState,
    core_switch: dict[str, Any],
    device: dict[str, Any],
    *,
    poe_enabled: bool,
) -> None:
    port_idx = _next_core_port(state)
    _add_port(core_switch, port_idx, poe_enabled=poe_enabled, rng=state.rng)
    _add_lldp_link(
        core_switch,
        device,
        local_port=port_idx,
        remote_port=1,
        remote_name=device["name"],
    )
    _add_lldp_link(
        device,
        core_switch,
        local_port=1,
        remote_port=port_idx,
        remote_name=core_switch["name"],
    )


def _add_lldp_link(
    source: dict[str, Any],
    target: dict[str, Any],
    *,
    local_port: int,
    remote_port: int,
    remote_name: str,
) -> None:
    source["lldp_info"].append(
        {
            "chassis_id": target["mac"],
            "port_id": f"Port {remote_port}",
            "port_desc": remote_name,
            "local_port_idx": local_port,
            "local_port_name": f"Port {local_port}",
        }
    )


def _add_port(
    device: dict[str, Any],
    port_idx: int,
    *,
    poe_enabled: bool,
    rng: random.Random,
) -> None:
    device["port_table"].append(
        {
            "port_idx": port_idx,
            "name": f"Port {port_idx}",
            "ifname": f"eth{port_idx}",
            "is_uplink": False,
            "poe_enable": poe_enabled,
            "port_poe": poe_enabled,
            "poe_class": 4 if poe_enabled else 0,
            "poe_power": round(rng.uniform(2.0, 6.0), 2) if poe_enabled else 0.0,
            "poe_good": poe_enabled,
            "poe_voltage": round(rng.uniform(44.0, 52.0), 1) if poe_enabled else 0.0,
            "poe_current": round(rng.uniform(0.05, 0.12), 3) if poe_enabled else 0.0,
        }
    )


def _next_core_port(state: _MockState) -> int:
    port_idx = state.core_port_next
    state.core_port_next += 1
    return port_idx


def _unique_name(state: _MockState, prefix: str) -> str:
    name = prefix
    while name in state.used_names:
        name = f"{prefix} {state.rng.randint(2, 9)}"
    state.used_names.add(name)
    return name


def _unique_client_name(state: _MockState) -> str:
    name = state.fake.first_name()
    while name in state.used_names:
        name = state.fake.first_name()
    state.used_names.add(name)
    return name


def _unique_room(state: _MockState) -> str:
    room = state.fake.word().title()
    while room in state.used_rooms:
        room = state.fake.word().title()
    state.used_rooms.add(room)
    return room


def _unique_mac(state: _MockState) -> str:
    mac = state.fake.mac_address()
    while mac in state.used_macs:
        mac = state.fake.mac_address()
    state.used_macs.add(mac)
    return mac


def _unique_ip(state: _MockState) -> str:
    ip = state.fake.ipv4_private()
    while ip in state.used_ips:
        ip = state.fake.ipv4_private()
    state.used_ips.add(ip)
    return ip
