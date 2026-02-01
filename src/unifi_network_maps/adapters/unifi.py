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
from typing import IO, TYPE_CHECKING

from ..io.paths import resolve_cache_dir
from ..model.vlans import build_vlan_info, normalize_networks
from .config import Config

if TYPE_CHECKING:
    from unifi_controller_api import UnifiController

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


def _device_attr(device: object, name: str) -> object | None:
    if isinstance(device, dict):
        return device.get(name)
    return getattr(device, name, None)


def _first_attr(device: object, *names: str) -> object | None:
    for name in names:
        value = _device_attr(device, name)
        if value is not None:
            return value
    return None


def _as_list(value: object | None) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str | bytes):
        return []
    try:
        return list(value)  # type: ignore[arg-type]
    except TypeError:
        return []


def _serialize_lldp_entry(entry: object) -> dict[str, object]:
    return {
        "chassis_id": _first_attr(entry, "chassis_id", "chassisId"),
        "port_id": _first_attr(entry, "port_id", "portId"),
        "port_desc": _first_attr(entry, "port_desc", "portDesc", "port_descr", "portDescr"),
        "local_port_name": _first_attr(entry, "local_port_name", "localPortName"),
        "local_port_idx": _first_attr(entry, "local_port_idx", "localPortIdx"),
    }


def _serialize_lldp_entries(value: object | None) -> list[dict[str, object]]:
    entries = _as_list(value)
    serialized: list[dict[str, object]] = []
    for entry in entries:
        data = _serialize_lldp_entry(entry)
        if data.get("chassis_id") and data.get("port_id"):
            serialized.append(data)
    return serialized


def _serialize_port_entry(entry: object) -> dict[str, object]:
    aggregation_group = _first_attr(
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
    return {
        "port_idx": _first_attr(entry, "port_idx", "portIdx"),
        "name": _first_attr(entry, "name"),
        "ifname": _first_attr(entry, "ifname"),
        "speed": _first_attr(entry, "speed"),
        "aggregation_group": aggregation_group,
        "port_poe": _first_attr(entry, "port_poe"),
        "poe_enable": _first_attr(entry, "poe_enable"),
        "poe_good": _first_attr(entry, "poe_good"),
        "poe_power": _first_attr(entry, "poe_power"),
    }


def _serialize_port_table(value: object | None) -> list[dict[str, object]]:
    return [_serialize_port_entry(entry) for entry in _as_list(value)]


def _serialize_uplink(value: object | None) -> dict[str, object] | None:
    if value is None:
        return None
    data = {
        "uplink_mac": _first_attr(value, "uplink_mac", "uplink_device_mac"),
        "uplink_device_name": _first_attr(value, "uplink_device_name", "uplink_name"),
        "uplink_remote_port": _first_attr(value, "uplink_remote_port", "port_idx"),
    }
    if any(item is not None for item in data.values()):
        return data
    return None


def _device_lldp_value(device: object) -> object | None:
    lldp_info = _device_attr(device, "lldp_info")
    if lldp_info is None:
        lldp_info = _device_attr(device, "lldp")
    if lldp_info is None:
        lldp_info = _device_attr(device, "lldp_table")
    return lldp_info


def _device_uplink_fields(device: object) -> dict[str, object | None]:
    return {
        "uplink": _serialize_uplink(_device_attr(device, "uplink")),
        "last_uplink": _serialize_uplink(_device_attr(device, "last_uplink")),
        "uplink_mac": _first_attr(device, "uplink_mac", "uplink_device_mac"),
        "uplink_device_name": _device_attr(device, "uplink_device_name"),
        "uplink_remote_port": _device_attr(device, "uplink_remote_port"),
        "last_uplink_mac": _device_attr(device, "last_uplink_mac"),
    }


def _serialize_device_for_cache(device: object) -> dict[str, object]:
    payload = {
        "name": _device_attr(device, "name"),
        "model_name": _device_attr(device, "model_name"),
        "model": _device_attr(device, "model"),
        "mac": _device_attr(device, "mac"),
        "ip": _first_attr(device, "ip", "ip_address"),
        "type": _first_attr(device, "type", "device_type"),
        "displayable_version": _first_attr(device, "displayable_version", "version"),
        "lldp_info": _serialize_lldp_entries(_device_lldp_value(device)),
        "port_table": _serialize_port_table(_device_attr(device, "port_table")),
    }
    payload.update(_device_uplink_fields(device))
    return payload


def _serialize_devices_for_cache(devices: Sequence[object]) -> list[dict[str, object]]:
    return [_serialize_device_for_cache(device) for device in devices]


def _serialize_network_for_cache(network: object) -> dict[str, object]:
    return {
        "name": _first_attr(network, "name", "network_name", "networkName"),
        "vlan": _first_attr(network, "vlan", "vlan_id", "vlanId", "vlanid"),
        "vlan_enabled": _first_attr(network, "vlan_enabled", "vlanEnabled"),
        "purpose": _first_attr(network, "purpose"),
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
        return max(1, int(value))
    logger.warning("Invalid UNIFI_RETRY_ATTEMPTS value: %s", value)
    return 2


def _retry_backoff_seconds() -> float:
    value = os.environ.get("UNIFI_RETRY_BACKOFF_SECONDS", "").strip()
    if not value:
        return 0.5
    try:
        return max(0.0, float(value))
    except ValueError:
        logger.warning("Invalid UNIFI_RETRY_BACKOFF_SECONDS value: %s", value)
        return 0.5


def _request_timeout_seconds() -> float | None:
    value = os.environ.get("UNIFI_REQUEST_TIMEOUT_SECONDS", "").strip()
    if not value:
        return None
    try:
        return max(0.0, float(value))
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
    config: Config,
    *,
    site: str | None = None,
    detailed: bool = True,
    use_cache: bool = True,
) -> Sequence[object]:
    """Fetch devices from UniFi Controller.

    Uses `unifi-controller-api` to authenticate and return device objects.
    """
    try:
        from unifi_controller_api import UnifiAuthenticationError
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"devices_{_cache_key(config.url, site_name, str(detailed))}.json"
    if use_cache and _is_cache_dir_safe(cache_path.parent):
        cached = _load_cache(cache_path, ttl_seconds)
        stale_cached, cache_age = _load_cache_with_age(cache_path)
    else:
        cached = None
        stale_cached, cache_age = None, None
    if cached is not None:
        logger.debug("Using cached devices (%d)", len(cached))
        return cached

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.debug("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    def _fetch() -> Sequence[object]:
        return controller.get_unifi_site_device(site_name=site_name, detailed=detailed, raw=False)

    try:
        devices = _call_with_retries("device fetch", _fetch)
    except Exception as exc:  # noqa: BLE001 - fallback to cache
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
    try:
        from unifi_controller_api import UnifiAuthenticationError
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"clients_{_cache_key(config.url, site_name)}.json"
    if use_cache and _is_cache_dir_safe(cache_path.parent):
        cached = _load_cache(cache_path, ttl_seconds)
        stale_cached, cache_age = _load_cache_with_age(cache_path)
    else:
        cached = None
        stale_cached, cache_age = None, None
    if cached is not None:
        logger.debug("Using cached clients (%d)", len(cached))
        return cached

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.debug("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    def _fetch() -> Sequence[object]:
        return controller.get_unifi_site_client(site_name=site_name, raw=True)

    try:
        clients = _call_with_retries("client fetch", _fetch)
    except Exception as exc:  # noqa: BLE001 - fallback to cache
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
    try:
        from unifi_controller_api import UnifiAuthenticationError
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    site_name = site or config.site
    ttl_seconds = _cache_ttl_seconds()
    cache_path = _cache_dir() / f"networks_{_cache_key(config.url, site_name)}.json"
    if use_cache and _is_cache_dir_safe(cache_path.parent):
        cached = _load_cache(cache_path, ttl_seconds)
        stale_cached, cache_age = _load_cache_with_age(cache_path)
    else:
        cached = None
        stale_cached, cache_age = None, None
    if cached is not None:
        logger.debug("Using cached networks (%d)", len(cached))
        return cached

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.debug("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    def _fetch() -> Sequence[object]:
        try:
            return controller.get_unifi_site_networkconf(site_name=site_name, raw=False)
        except Exception as exc:  # noqa: BLE001 - fallback to raw network data
            logger.warning("Networkconf model parse failed; retrying raw fetch: %s", exc)
            return controller.get_unifi_site_networkconf(site_name=site_name, raw=True)

    try:
        networks = _call_with_retries("network fetch", _fetch)
    except Exception as exc:  # noqa: BLE001 - fallback to cache
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
