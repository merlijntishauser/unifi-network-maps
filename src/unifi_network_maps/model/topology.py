"""Topology data classes and type definitions.

This module contains the core data structures for representing network topology.
For functions, see:
- classify: Device/client type classification
- edges: Edge building and topology construction
- clients: Client handling
- wan: WAN interface extraction
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .helpers import normalize_mac
from .lldp import LLDPEntry

if TYPE_CHECKING:
    from .connection import ConnectionInfo
    from .diff import TopologyDiff


@dataclass(frozen=True)
class UplinkInfo:
    """Information about a device's uplink connection."""

    mac: str | None
    name: str | None
    port: int | None


@dataclass(frozen=True)
class PortInfo:
    """Information about a switch/gateway port."""

    port_idx: int | None
    name: str | None
    ifname: str | None
    speed: int | None
    aggregation_group: str | None
    port_poe: bool
    poe_enable: bool
    poe_good: bool
    poe_power: float | None
    up: bool | None = None
    native_vlan: int | None = None
    tagged_vlans: tuple[int, ...] = ()
    wan_networkconf_id: str | None = None


@dataclass(frozen=True)
class Device:
    """A network device (gateway, switch, or access point)."""

    name: str
    model_name: str
    model: str
    mac: str
    ip: str
    type: str
    lldp_info: list[LLDPEntry]
    port_table: list[PortInfo] = field(default_factory=list)
    poe_ports: dict[int, bool] = field(default_factory=dict)
    uplink: UplinkInfo | None = None
    last_uplink: UplinkInfo | None = None
    version: str = ""
    in_gateway_mode: bool | None = None


@dataclass(frozen=True)
class Edge:
    """A connection between two nodes in the topology."""

    left: str
    right: str
    label: str | None = None
    poe: bool = False
    wireless: bool = False
    speed: int | None = None
    channel: int | None = None
    vlans: tuple[int, ...] = ()
    active_vlans: tuple[int, ...] = ()
    is_trunk: bool = False
    connection: ConnectionInfo | None = None


@dataclass(frozen=True)
class WanInterface:
    """Information about a WAN interface on a gateway."""

    port_idx: int
    link_speed: int | None
    ip_address: str | None
    enabled: bool
    label: str | None = None
    isp_speed: str | None = None


@dataclass(frozen=True)
class WanInfo:
    """WAN interface information for a gateway device."""

    wan1: WanInterface | None = None
    wan2: WanInterface | None = None


@dataclass(frozen=True)
class TopologyResult:
    """Result of building a topology."""

    raw_edges: list[Edge]
    tree_edges: list[Edge]


# Type aliases for maps used in edge building
type DeviceSource = object
type PortMap = dict[tuple[str, str], str]
type PoeMap = dict[tuple[str, str], bool]
type SpeedMap = dict[tuple[str, str], int]
type ClientPortMap = dict[str, list[tuple[int, str]]]
type VlanMap = dict[tuple[str, str], tuple[int, ...]]


def build_device_index(devices: Iterable[Device]) -> dict[str, str]:
    """Build MAC to name index for devices."""
    index: dict[str, str] = {}
    for device in devices:
        index[normalize_mac(device.mac)] = device.name
    return index


# --- Topology class for serialization and diff ---


@dataclass
class Topology:
    """A complete network topology snapshot for serialization and comparison."""

    devices: list[Device] = field(default_factory=list)
    clients: list[dict[str, object]] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    timestamp: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize topology to a JSON-compatible dictionary."""
        from .snapshot import client_to_dict, device_to_dict, edge_to_dict

        return {
            "version": 1,
            "timestamp": self.timestamp,
            "devices": [device_to_dict(d) for d in self.devices],
            "clients": [client_to_dict(c) for c in self.clients],  # type: ignore[arg-type]
            "edges": [edge_to_dict(e) for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Topology:
        """Deserialize topology from a dictionary."""
        from .snapshot import client_from_dict, device_from_dict, edge_from_dict

        devices_data = data.get("devices", [])
        clients_data = data.get("clients", [])
        edges_data = data.get("edges", [])

        devices = [device_from_dict(d) for d in devices_data]  # type: ignore[arg-type]
        clients = [client_from_dict(c) for c in clients_data]  # type: ignore[arg-type]
        edges = [edge_from_dict(e) for e in edges_data]  # type: ignore[arg-type]

        timestamp = data.get("timestamp")
        return cls(
            devices=devices,
            clients=clients,
            edges=edges,
            timestamp=timestamp if isinstance(timestamp, str) else None,
        )

    def diff(self, other: Topology) -> TopologyDiff:
        """Compare this topology with another and return differences."""
        from .diff import compare_topologies

        return compare_topologies(
            old_devices=self.devices,
            new_devices=other.devices,
            old_clients=self.clients,  # type: ignore[arg-type]
            new_clients=other.clients,  # type: ignore[arg-type]
            old_edges=self.edges,
            new_edges=other.edges,
            old_timestamp=self.timestamp,
            new_timestamp=other.timestamp,
        )


__all__ = [
    # Data classes
    "Device",
    "Edge",
    "PortInfo",
    "TopologyResult",
    "Topology",
    "UplinkInfo",
    "WanInfo",
    "WanInterface",
    # Functions
    "build_device_index",
]
