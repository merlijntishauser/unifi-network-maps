"""UniFi API integration."""

from __future__ import annotations

import logging
from typing import Iterable

from .config import Config

logger = logging.getLogger(__name__)


def fetch_devices(config: Config, *, site: str | None = None, detailed: bool = True) -> Iterable[object]:
    """Fetch devices from UniFi Controller.

    Uses `unifi-controller-api` to authenticate and return device objects.
    """
    try:
        from unifi_controller_api import UnifiController
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    controller = UnifiController(
        host=config.url,
        username=config.user,
        password=config.password,
        site=site or config.site,
        ssl_verify=config.verify_ssl,
    )

    if hasattr(controller, "list_devices"):
        try:
            devices = controller.list_devices(detailed=detailed)
        except TypeError:
            devices = controller.list_devices()
    elif hasattr(controller, "get_devices"):
        try:
            devices = controller.get_devices(detailed=detailed)
        except TypeError:
            devices = controller.get_devices()
    else:
        raise RuntimeError("UnifiController does not expose a device listing method")

    logger.info("Fetched %d devices", len(devices))
    return devices
