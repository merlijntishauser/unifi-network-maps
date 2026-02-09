"""Adapters for external data sources."""

from .config import Config
from .dns import resolve_hostnames
from .unifi import fetch_clients, fetch_devices, fetch_networks

__all__ = [
    "Config",
    "fetch_clients",
    "fetch_devices",
    "fetch_networks",
    "resolve_hostnames",
]
