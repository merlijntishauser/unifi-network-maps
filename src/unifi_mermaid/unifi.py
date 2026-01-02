"""UniFi API integration."""

from __future__ import annotations

import hashlib
import logging
import os
import pickle
import time
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from .config import Config

if TYPE_CHECKING:
    from unifi_controller_api import UnifiController

logger = logging.getLogger(__name__)


def _cache_dir() -> Path:
    return Path(os.environ.get("UNIFI_CACHE_DIR", ".cache/unifi_mermaid"))


def _cache_ttl_seconds() -> int:
    value = os.environ.get("UNIFI_CACHE_TTL_SECONDS", "").strip()
    if not value:
        return 3600
    if value.isdigit():
        return int(value)
    logger.warning("Invalid UNIFI_CACHE_TTL_SECONDS value: %s", value)
    return 3600


def _cache_key(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:24]


def _load_cache(path: Path, ttl_seconds: int) -> object | None:
    if ttl_seconds <= 0 or not path.exists():
        return None
    try:
        payload = pickle.loads(path.read_bytes())
    except Exception as exc:
        logger.debug("Failed to read cache %s: %s", path, exc)
        return None
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, int | float):
        return None
    if time.time() - timestamp > ttl_seconds:
        return None
    return payload.get("data")


def _save_cache(path: Path, data: object) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": time.time(), "data": data}
        path.write_bytes(pickle.dumps(payload))
    except Exception as exc:
        logger.debug("Failed to write cache %s: %s", path, exc)


def _init_controller(config: Config, *, is_udm_pro: bool) -> UnifiController:
    from unifi_controller_api import UnifiController

    return UnifiController(
        controller_url=config.url,
        username=config.user,
        password=config.password,
        is_udm_pro=is_udm_pro,
        verify_ssl=config.verify_ssl,
    )


def fetch_devices(
    config: Config, *, site: str | None = None, detailed: bool = True
) -> Iterable[object]:
    """Fetch devices from UniFi Controller.

    Uses `unifi-controller-api` to authenticate and return device objects.
    """
    try:
        from unifi_controller_api import UnifiAuthenticationError
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"devices_{_cache_key(config.url, site_name, str(detailed))}.pkl"
    cached = _load_cache(cache_path, ttl_seconds)
    if cached is not None:
        logger.info("Using cached devices (%d)", len(cached))
        return cached

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.info("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    devices = controller.get_unifi_site_device(site_name=site_name, detailed=detailed, raw=False)
    _save_cache(cache_path, devices)
    logger.info("Fetched %d devices", len(devices))
    return devices


def fetch_clients(config: Config, *, site: str | None = None) -> Iterable[object]:
    """Fetch active clients from UniFi Controller."""
    try:
        from unifi_controller_api import UnifiAuthenticationError
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"clients_{_cache_key(config.url, site_name)}.pkl"
    cached = _load_cache(cache_path, ttl_seconds)
    if cached is not None:
        logger.info("Using cached clients (%d)", len(cached))
        return cached

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.info("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    clients = controller.get_unifi_site_client(site_name=site_name, raw=True)
    _save_cache(cache_path, clients)
    logger.info("Fetched %d clients", len(clients))
    return clients
