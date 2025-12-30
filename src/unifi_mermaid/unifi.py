"""UniFi API integration."""

from __future__ import annotations

import logging
from typing import Iterable

from .config import Config

logger = logging.getLogger(__name__)


def _init_controller(config: Config, *, is_udm_pro: bool) -> "UnifiController":
    from unifi_controller_api import UnifiController

    return UnifiController(
        controller_url=config.url,
        username=config.user,
        password=config.password,
        is_udm_pro=is_udm_pro,
        verify_ssl=config.verify_ssl,
    )


def fetch_devices(config: Config, *, site: str | None = None, detailed: bool = True) -> Iterable[object]:
    """Fetch devices from UniFi Controller.

    Uses `unifi-controller-api` to authenticate and return device objects.
    """
    try:
        from unifi_controller_api import UnifiAuthenticationError
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    site_name = site or config.site

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError as exc:
        logger.info("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    devices = controller.get_unifi_site_device(site_name=site_name, detailed=detailed, raw=False)
    logger.info("Fetched %d devices", len(devices))
    return devices
