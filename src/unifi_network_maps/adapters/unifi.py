"""UniFi API integration."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import stat
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import IO, TYPE_CHECKING

from .config import Config

if TYPE_CHECKING:
    from unifi_controller_api import UnifiController

logger = logging.getLogger(__name__)


def _cache_dir() -> Path:
    return Path(os.environ.get("UNIFI_CACHE_DIR", ".cache/unifi_network_maps"))


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


def _call_with_retries[T](operation: str, func: Callable[[], T]) -> T:
    attempts = _retry_attempts()
    backoff = _retry_backoff_seconds()
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
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
        logger.info("Using cached devices (%d)", len(cached))
        return cached

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.info("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    def _fetch() -> Sequence[object]:
        return controller.get_unifi_site_device(site_name=site_name, detailed=detailed, raw=True)

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
        _save_cache(cache_path, devices)
    logger.info("Fetched %d devices", len(devices))
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
        logger.info("Using cached clients (%d)", len(cached))
        return cached

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.info("UDM Pro authentication failed, retrying legacy auth")
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
    logger.info("Fetched %d clients", len(clients))
    return clients
