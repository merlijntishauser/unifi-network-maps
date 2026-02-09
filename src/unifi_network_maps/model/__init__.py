"""Network topology model."""

from .clients import build_client_edges, build_node_type_map
from .edges import build_device_index, build_topology, group_devices_by_type
from .mock import MockOptions, generate_mock_payload
from .topology import Device, Edge, TopologyResult, WanInfo
from .topology_coerce import normalize_devices
from .wan import extract_wan_info

__all__ = [
    "Device",
    "Edge",
    "MockOptions",
    "TopologyResult",
    "WanInfo",
    "build_client_edges",
    "build_device_index",
    "build_node_type_map",
    "build_topology",
    "extract_wan_info",
    "generate_mock_payload",
    "group_devices_by_type",
    "normalize_devices",
]
