"""UniFi API integration."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import stat
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from ..io.paths import resolve_cache_dir
from ..model.helpers import as_list, first_attr, get_field
from ..model.lldp import coerce_lldp
from ..model.snapshot import lldp_entry_to_dict
from ..model.vlans import build_vlan_info, normalize_networks
from .config import Config
from .unifi_api import UnifiAuthError, UnifiClient

logger = logging.getLogger(__name__)


def _cache_dir() -> Path:
    default_dir = ".cache/unifi_network_maps"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        default_dir = str(Path(tempfile.gettempdir()) / f"unifi_network_maps_pytest_{os.getpid()}")
    value = os.environ.get("UNIFI_CACHE_DIR", default_dir)
    try:
        return resolve_cache_dir(value)
    except ValueError as exc:
        logger.warning("Invalid UNIFI_CACHE_DIR (%s); using default: %s", value, exc)
        return resolve_cache_dir(".cache/unifi_network_maps")


def _serialize_lldp_entries(value: object | None) -> list[dict[str, object]]:
    serialized: list[dict[str, object]] = []
    for entry in as_list(value):
        try:
            lldp = coerce_lldp(entry)
        except ValueError:
            continue
        serialized.append(lldp_entry_to_dict(lldp))
    return serialized


def _serialize_port_entry(entry: object) -> dict[str, object]:
    aggregation_group = first_attr(
        entry,
        "aggregation_group",
        "aggregation_id",
        "aggregate_id",
        "agg_id",
        "lag_id",
        "lag_group",
        "link_aggregation_group",
        "link_aggregation_id",
        "aggregate",
        "aggregated_by",
    )
    native_vlan = first_attr(
        entry,
        "native_networkconf_id",
        "port_vlan",
        "vlan",
        "native_vlan",
        "pvid",
    )
    tagged_vlans = first_attr(
        entry,
        "tagged_vlan_mgmt",
        "tagged_vlans",
        "vlan_trunk_mgmt",
        "allowed_vlans",
    )
    return {
        "port_idx": first_attr(entry, "port_idx", "portIdx"),
        "name": first_attr(entry, "name"),
        "ifname": first_attr(entry, "ifname"),
        "speed": first_attr(entry, "speed"),
        "up": first_attr(entry, "up"),
        "aggregation_group": aggregation_group,
        "port_poe": first_attr(entry, "port_poe"),
        "poe_enable": first_attr(entry, "poe_enable"),
        "poe_good": first_attr(entry, "poe_good"),
        "poe_power": first_attr(entry, "poe_power"),
        "native_vlan": native_vlan,
        "tagged_vlans": tagged_vlans,
        "wan_networkconf_id": first_attr(entry, "wan_networkconf_id"),
    }


def _serialize_port_table(value: object | None) -> list[dict[str, object]]:
    return [_serialize_port_entry(entry) for entry in as_list(value)]


def _serialize_uplink(value: object | None) -> dict[str, object] | None:
    if value is None:
        return None
    data = {
        "uplink_mac": first_attr(value, "uplink_mac", "uplink_device_mac"),
        "uplink_device_name": first_attr(value, "uplink_device_name", "uplink_name"),
        "uplink_remote_port": first_attr(value, "uplink_remote_port", "port_idx"),
    }
    if any(item is not None for item in data.values()):
        return data
    return None


def _device_lldp_value(device: object) -> object | None:
    lldp_info = get_field(device, "lldp_info")
    if lldp_info is None:
        lldp_info = get_field(device, "lldp")
    if lldp_info is None:
        lldp_info = get_field(device, "lldp_table")
    return lldp_info


def _device_uplink_fields(device: object) -> dict[str, object | None]:
    return {
        "uplink": _serialize_uplink(get_field(device, "uplink")),
        "last_uplink": _serialize_uplink(get_field(device, "last_uplink")),
        "uplink_mac": first_attr(device, "uplink_mac", "uplink_device_mac"),
        "uplink_device_name": get_field(device, "uplink_device_name"),
        "uplink_remote_port": get_field(device, "uplink_remote_port"),
        "last_uplink_mac": get_field(device, "last_uplink_mac"),
    }


def _serialize_device_for_cache(device: object) -> dict[str, object]:
    payload = {
        "name": get_field(device, "name"),
        "model_name": get_field(device, "model_name"),
        "model": get_field(device, "model"),
        "mac": get_field(device, "mac"),
        "ip": first_attr(device, "ip", "ip_address"),
        "type": first_attr(device, "type", "device_type"),
        "in_gateway_mode": get_field(device, "in_gateway_mode"),
        "displayable_version": first_attr(device, "displayable_version", "version"),
        "lldp_info": _serialize_lldp_entries(_device_lldp_value(device)),
        "port_table": _serialize_port_table(get_field(device, "port_table")),
    }
    payload.update(_device_uplink_fields(device))
    return payload


def _serialize_devices_for_cache(devices: Sequence[object]) -> list[dict[str, object]]:
    return [_serialize_device_for_cache(device) for device in devices]


def _serialize_network_for_cache(network: object) -> dict[str, object]:
    return {
        "_id": first_attr(network, "_id", "id", "network_id", "networkId"),
        "name": first_attr(network, "name", "network_name", "networkName"),
        "vlan": first_attr(network, "vlan", "vlan_id", "vlanId", "vlanid"),
        "vlan_enabled": first_attr(network, "vlan_enabled", "vlanEnabled"),
        "purpose": first_attr(network, "purpose"),
        "enabled": first_attr(network, "enabled", "wan_enabled"),
    }


def _serialize_networks_for_cache(networks: Sequence[object]) -> list[dict[str, object]]:
    return [_serialize_network_for_cache(network) for network in networks]


def _cache_lock_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".lock")


def _acquire_cache_lock(lock_file: IO[str]) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)


def _release_cache_lock(lock_file: IO[str]) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextmanager
def _cache_lock(path: Path) -> Iterator[None]:
    lock_path = _cache_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            _acquire_cache_lock(lock_file)
            yield
        finally:
            try:
                _release_cache_lock(lock_file)
            except OSError:
                logger.debug("Failed to release cache lock %s", lock_path)


def _is_cache_dir_safe(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        logger.warning("Failed to stat cache dir %s: %s", path, exc)
        return False
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        logger.warning("Cache dir %s is group/world-writable; skipping cache", path)
        return False
    return True


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


def _load_cache(path: Path, ttl_seconds: int) -> Sequence[object] | None:
    data, age = _load_cache_with_age(path)
    if data is None:
        return None
    if ttl_seconds <= 0:
        return None
    if age is None or age > ttl_seconds:
        return None
    return data


def _load_cache_with_age(path: Path) -> tuple[Sequence[object] | None, float | None]:
    if not path.exists():
        return None, None
    try:
        with _cache_lock(path):
            payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("Failed to read cache %s: %s", path, exc)
        return None, None
    if not isinstance(payload, dict):
        logger.debug("Cached payload at %s is not a dict", path)
        return None, None
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, int | float):
        return None, None
    data = payload.get("data")
    if not isinstance(data, list):
        logger.debug("Cached payload at %s is not a list", path)
        return None, None
    return data, time.time() - timestamp


def _save_cache(path: Path, data: Sequence[object]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not _is_cache_dir_safe(path.parent):
            return
        payload = {"timestamp": time.time(), "data": data}
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        with _cache_lock(path):
            tmp_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
            tmp_path.replace(path)
    except Exception as exc:
        logger.debug("Failed to write cache %s: %s", path, exc)


def _retry_attempts() -> int:
    value = os.environ.get("UNIFI_RETRY_ATTEMPTS", "").strip()
    if not value:
        return 2
    if value.isdigit():
        return min(max(1, int(value)), 20)
    logger.warning("Invalid UNIFI_RETRY_ATTEMPTS value: %s", value)
    return 2


def _retry_backoff_seconds() -> float:
    value = os.environ.get("UNIFI_RETRY_BACKOFF_SECONDS", "").strip()
    if not value:
        return 0.5
    try:
        return min(max(0.0, float(value)), 60.0)
    except ValueError:
        logger.warning("Invalid UNIFI_RETRY_BACKOFF_SECONDS value: %s", value)
        return 0.5


def _request_timeout_seconds() -> float | None:
    value = os.environ.get("UNIFI_REQUEST_TIMEOUT_SECONDS", "").strip()
    if not value:
        return None
    try:
        return min(max(0.0, float(value)), 300.0)
    except ValueError:
        logger.warning("Invalid UNIFI_REQUEST_TIMEOUT_SECONDS value: %s", value)
        return None


def _call_with_timeout[T](operation: str, func: Callable[[], T], timeout: float | None) -> T:
    if timeout is None or timeout <= 0:
        return func()
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"{operation} timed out after {timeout:.2f}s") from exc


def _call_with_retries[T](operation: str, func: Callable[[], T]) -> T:
    attempts = _retry_attempts()
    backoff = _retry_backoff_seconds()
    timeout = _request_timeout_seconds()
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _call_with_timeout(operation, func, timeout)
        except Exception as exc:  # noqa: BLE001 - surface full error after retries
            last_exc = exc
            logger.warning("Failed %s attempt %d/%d: %s", operation, attempt, attempts, exc)
            if attempt < attempts and backoff > 0:
                time.sleep(backoff * attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Failed {operation}")


def _create_client(config: Config, *, is_udm_pro: bool) -> UnifiClient:
    return UnifiClient(
        url=config.url,
        username=config.user,
        password=config.password,
        is_udm_pro=is_udm_pro,
        verify_ssl=config.verify_ssl,
    )


def _is_rate_limited(exc: Exception) -> bool:
    return "429" in str(exc)


def _connect_and_fetch(
    config: Config,
    operation: str,
    fetch_fn: Callable[[UnifiClient], Callable[[], Sequence[object]]],
) -> Sequence[object]:
    """Authenticate and fetch data, with UDM Pro / legacy auth fallback.

    On ``UnifiAuthError`` that isn't rate-limited, retries with
    legacy auth.  Any other error (rate limit, network, etc.) propagates
    to the caller's stale-cache handler.
    """
    try:
        client = _create_client(config, is_udm_pro=True)
    except UnifiAuthError as exc:
        if _is_rate_limited(exc):
            raise
        logger.debug("UDM Pro authentication failed, retrying legacy auth")
        client = _create_client(config, is_udm_pro=False)

    return _call_with_retries(operation, fetch_fn(client))


def fetch_devices(
    config: Config,
    *,
    site: str | None = None,
    detailed: bool = True,
    use_cache: bool = True,
) -> Sequence[object]:
    """Fetch devices from UniFi Controller."""
    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"devices_{_cache_key(config.url, site_name, str(detailed))}.json"
    cache_safe = use_cache and _is_cache_dir_safe(cache_path.parent)
    if cache_safe:
        cached = _load_cache(cache_path, ttl_seconds)
        if cached is not None:
            logger.debug("Using cached devices (%d)", len(cached))
            return cached

    def _make_fetch(client: UnifiClient) -> Callable[[], Sequence[object]]:
        def _fetch() -> Sequence[object]:
            return client.get_devices(site_name, detailed=detailed)

        return _fetch

    try:
        devices = _connect_and_fetch(config, "device fetch", _make_fetch)
    except Exception as exc:  # noqa: BLE001 - fallback to cache
        stale_cached, cache_age = _load_cache_with_age(cache_path) if cache_safe else (None, None)
        if stale_cached is not None:
            logger.warning(
                "Device fetch failed; using stale cache (%ds old): %s",
                int(cache_age or 0),
                exc,
            )
            return stale_cached
        raise
    if use_cache:
        _save_cache(cache_path, _serialize_devices_for_cache(devices))
    logger.debug("Fetched %d devices", len(devices))
    return devices


def fetch_clients(
    config: Config,
    *,
    site: str | None = None,
    use_cache: bool = True,
) -> Sequence[object]:
    """Fetch active clients from UniFi Controller."""
    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"clients_{_cache_key(config.url, site_name)}.json"
    cache_safe = use_cache and _is_cache_dir_safe(cache_path.parent)
    if cache_safe:
        cached = _load_cache(cache_path, ttl_seconds)
        if cached is not None:
            logger.debug("Using cached clients (%d)", len(cached))
            return cached

    def _make_fetch(client: UnifiClient) -> Callable[[], Sequence[object]]:
        def _fetch() -> Sequence[object]:
            return client.get_clients(site_name)

        return _fetch

    try:
        clients = _connect_and_fetch(config, "client fetch", _make_fetch)
    except Exception as exc:  # noqa: BLE001 - fallback to cache
        stale_cached, cache_age = _load_cache_with_age(cache_path) if cache_safe else (None, None)
        if stale_cached is not None:
            logger.warning(
                "Client fetch failed; using stale cache (%ds old): %s",
                int(cache_age or 0),
                exc,
            )
            return stale_cached
        raise
    if use_cache:
        _save_cache(cache_path, clients)
    logger.debug("Fetched %d clients", len(clients))
    return clients


def fetch_networks(
    config: Config,
    *,
    site: str | None = None,
    use_cache: bool = True,
) -> Sequence[object]:
    """Fetch network inventory from UniFi Controller."""
    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"networks_{_cache_key(config.url, site_name)}.json"
    cache_safe = use_cache and _is_cache_dir_safe(cache_path.parent)
    if cache_safe:
        cached = _load_cache(cache_path, ttl_seconds)
        if cached is not None:
            logger.debug("Using cached networks (%d)", len(cached))
            return cached

    def _make_fetch(client: UnifiClient) -> Callable[[], Sequence[object]]:
        def _fetch() -> Sequence[object]:
            return client.get_networkconf(site_name)

        return _fetch

    try:
        networks = _connect_and_fetch(config, "network fetch", _make_fetch)
    except Exception as exc:  # noqa: BLE001 - fallback to cache
        stale_cached, cache_age = _load_cache_with_age(cache_path) if cache_safe else (None, None)
        if stale_cached is not None:
            logger.warning(
                "Network fetch failed; using stale cache (%ds old): %s",
                int(cache_age or 0),
                exc,
            )
            return stale_cached
        raise
    if use_cache:
        _save_cache(cache_path, _serialize_networks_for_cache(networks))
    logger.debug("Fetched %d networks", len(networks))
    return networks


def fetch_payload(
    config: Config,
    *,
    site: str | None = None,
    include_clients: bool = True,
    use_cache: bool = True,
) -> dict[str, list[object] | list[dict[str, object]]]:
    """Fetch devices, clients, and VLAN inventory for payload output."""
    devices = list(fetch_devices(config, site=site, detailed=True, use_cache=use_cache))
    clients = _fetch_payload_clients(
        config,
        site=site,
        include_clients=include_clients,
        use_cache=use_cache,
    )
    networks = list(fetch_networks(config, site=site, use_cache=use_cache))
    normalized_networks = normalize_networks(networks)
    vlan_info = build_vlan_info(clients, normalized_networks)
    return {
        "devices": devices,
        "clients": clients,
        "networks": normalized_networks,
        "vlan_info": vlan_info,
    }


def _fetch_payload_clients(
    config: Config,
    *,
    site: str | None,
    include_clients: bool,
    use_cache: bool,
) -> list[object]:
    if not include_clients:
        return []
    return list(fetch_clients(config, site=site, use_cache=use_cache))
