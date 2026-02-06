"""Serialization helpers for topology data structures.

Provides to_dict/from_dict conversions for persistence and transmission.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, TypeVar

from .connection import ConnectionInfo
from .lldp import LLDPEntry
from .topology import Device, Edge, PortInfo, UplinkInfo, WanInfo, WanInterface

T = TypeVar("T")


def _serialize_value(value: Any) -> Any:
    """Recursively serialize a value to JSON-compatible form."""
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, tuple):
        return list(_serialize_value(v) for v in value)
    if isinstance(value, list):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return _dataclass_to_dict(value)
    return str(value)


def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass instance to a dictionary."""
    result: dict[str, Any] = {}
    for field in fields(obj):
        value = getattr(obj, field.name)
        result[field.name] = _serialize_value(value)
    return result


# --- PortInfo ---


def port_info_to_dict(port: PortInfo) -> dict[str, Any]:
    """Serialize a PortInfo to a dictionary."""
    return _dataclass_to_dict(port)


def port_info_from_dict(data: dict[str, Any]) -> PortInfo:
    """Deserialize a PortInfo from a dictionary."""
    return PortInfo(
        port_idx=data.get("port_idx"),
        name=data.get("name"),
        ifname=data.get("ifname"),
        speed=data.get("speed"),
        aggregation_group=data.get("aggregation_group"),
        port_poe=data.get("port_poe", False),
        poe_enable=data.get("poe_enable", False),
        poe_good=data.get("poe_good", False),
        poe_power=data.get("poe_power"),
        up=data.get("up"),
        native_vlan=data.get("native_vlan"),
        tagged_vlans=tuple(data.get("tagged_vlans", [])),
        wan_networkconf_id=data.get("wan_networkconf_id"),
    )


# --- UplinkInfo ---


def uplink_info_to_dict(uplink: UplinkInfo) -> dict[str, Any]:
    """Serialize an UplinkInfo to a dictionary."""
    return _dataclass_to_dict(uplink)


def uplink_info_from_dict(data: dict[str, Any]) -> UplinkInfo:
    """Deserialize an UplinkInfo from a dictionary."""
    return UplinkInfo(
        mac=data.get("mac"),
        name=data.get("name"),
        port=data.get("port"),
    )


# --- LLDPEntry ---


def lldp_entry_to_dict(entry: LLDPEntry) -> dict[str, Any]:
    """Serialize an LLDPEntry to a dictionary."""
    return _dataclass_to_dict(entry)


def lldp_entry_from_dict(data: dict[str, Any]) -> LLDPEntry:
    """Deserialize an LLDPEntry from a dictionary."""
    return LLDPEntry(
        chassis_id=data.get("chassis_id", ""),
        port_id=data.get("port_id", ""),
        port_desc=data.get("port_desc"),
        local_port_name=data.get("local_port_name"),
        local_port_idx=data.get("local_port_idx"),
    )


# --- WanInterface ---


def wan_interface_to_dict(wan: WanInterface) -> dict[str, Any]:
    """Serialize a WanInterface to a dictionary."""
    return _dataclass_to_dict(wan)


def wan_interface_from_dict(data: dict[str, Any]) -> WanInterface:
    """Deserialize a WanInterface from a dictionary."""
    return WanInterface(
        port_idx=data.get("port_idx", 0),
        link_speed=data.get("link_speed"),
        ip_address=data.get("ip_address"),
        enabled=data.get("enabled", False),
        label=data.get("label"),
        isp_speed=data.get("isp_speed"),
    )


# --- WanInfo ---


def wan_info_to_dict(wan_info: WanInfo) -> dict[str, Any]:
    """Serialize a WanInfo to a dictionary."""
    result: dict[str, Any] = {}
    if wan_info.wan1:
        result["wan1"] = wan_interface_to_dict(wan_info.wan1)
    else:
        result["wan1"] = None
    if wan_info.wan2:
        result["wan2"] = wan_interface_to_dict(wan_info.wan2)
    else:
        result["wan2"] = None
    return result


def wan_info_from_dict(data: dict[str, Any]) -> WanInfo:
    """Deserialize a WanInfo from a dictionary."""
    wan1 = None
    wan2 = None
    if data.get("wan1"):
        wan1 = wan_interface_from_dict(data["wan1"])
    if data.get("wan2"):
        wan2 = wan_interface_from_dict(data["wan2"])
    return WanInfo(wan1=wan1, wan2=wan2)


# --- Device ---


def device_to_dict(device: Device) -> dict[str, Any]:
    """Serialize a Device to a dictionary."""
    return {
        "name": device.name,
        "model_name": device.model_name,
        "model": device.model,
        "mac": device.mac,
        "ip": device.ip,
        "type": device.type,
        "lldp_info": [lldp_entry_to_dict(e) for e in device.lldp_info],
        "port_table": [port_info_to_dict(p) for p in device.port_table],
        "poe_ports": {str(k): v for k, v in device.poe_ports.items()},
        "uplink": uplink_info_to_dict(device.uplink) if device.uplink else None,
        "last_uplink": uplink_info_to_dict(device.last_uplink) if device.last_uplink else None,
        "version": device.version,
    }


def device_from_dict(data: dict[str, Any]) -> Device:
    """Deserialize a Device from a dictionary."""
    lldp_info = [lldp_entry_from_dict(e) for e in data.get("lldp_info", [])]
    port_table = [port_info_from_dict(p) for p in data.get("port_table", [])]
    poe_ports = {int(k): v for k, v in data.get("poe_ports", {}).items()}
    uplink = uplink_info_from_dict(data["uplink"]) if data.get("uplink") else None
    last_uplink = uplink_info_from_dict(data["last_uplink"]) if data.get("last_uplink") else None
    return Device(
        name=data.get("name", ""),
        model_name=data.get("model_name", ""),
        model=data.get("model", ""),
        mac=data.get("mac", ""),
        ip=data.get("ip", ""),
        type=data.get("type", ""),
        lldp_info=lldp_info,
        port_table=port_table,
        poe_ports=poe_ports,
        uplink=uplink,
        last_uplink=last_uplink,
        version=data.get("version", ""),
    )


# --- ConnectionInfo ---


def connection_info_to_dict(conn: ConnectionInfo) -> dict[str, Any]:
    """Serialize a ConnectionInfo to a dictionary."""
    return _dataclass_to_dict(conn)


def connection_info_from_dict(data: dict[str, Any]) -> ConnectionInfo:
    """Deserialize a ConnectionInfo from a dictionary."""
    return ConnectionInfo(
        signal_dbm=data.get("signal_dbm"),
        noise_dbm=data.get("noise_dbm"),
        tx_rate_mbps=data.get("tx_rate_mbps"),
        rx_rate_mbps=data.get("rx_rate_mbps"),
        satisfaction=data.get("satisfaction"),
        quality=data.get("quality"),
    )


# --- Edge ---


def edge_to_dict(edge: Edge) -> dict[str, Any]:
    """Serialize an Edge to a dictionary."""
    return {
        "left": edge.left,
        "right": edge.right,
        "label": edge.label,
        "poe": edge.poe,
        "wireless": edge.wireless,
        "speed": edge.speed,
        "channel": edge.channel,
        "vlans": list(edge.vlans),
        "active_vlans": list(edge.active_vlans),
        "is_trunk": edge.is_trunk,
        "connection": connection_info_to_dict(edge.connection) if edge.connection else None,
    }


def edge_from_dict(data: dict[str, Any]) -> Edge:
    """Deserialize an Edge from a dictionary."""
    connection = None
    if data.get("connection"):
        connection = connection_info_from_dict(data["connection"])
    return Edge(
        left=data.get("left", ""),
        right=data.get("right", ""),
        label=data.get("label"),
        poe=data.get("poe", False),
        wireless=data.get("wireless", False),
        speed=data.get("speed"),
        channel=data.get("channel"),
        vlans=tuple(data.get("vlans", [])),
        active_vlans=tuple(data.get("active_vlans", [])),
        is_trunk=data.get("is_trunk", False),
        connection=connection,
    )


# --- Client (dict-based, since clients come from API as dicts) ---


def client_to_dict(client: dict[str, Any]) -> dict[str, Any]:
    """Serialize a client dict, keeping only relevant fields."""
    relevant_keys = {
        "mac",
        "name",
        "hostname",
        "ip",
        "vlan",
        "vlan_id",
        "is_wired",
        "is_unifi",
        "is_unifi_device",
        "ap_mac",
        "sw_mac",
        "uplink_mac",
        "uplink_device_mac",
        "sw_port",
        "uplink_remote_port",
        "channel",
        "signal",
        "noise",
        "tx_rate",
        "rx_rate",
        "satisfaction",
        "oui",
        "vendor",
        "unifi_device_info_from_ucore",
    }
    return {k: v for k, v in client.items() if k in relevant_keys}


def client_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Deserialize a client dict (identity for now, but validates structure)."""
    return dict(data)
