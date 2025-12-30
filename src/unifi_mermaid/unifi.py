"""UniFi API integration."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

from .config import Config

if TYPE_CHECKING:
    from unifi_controller_api import UnifiController

logger = logging.getLogger(__name__)


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

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.info("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    devices = controller.get_unifi_site_device(site_name=site_name, detailed=detailed, raw=False)
    logger.info("Fetched %d devices", len(devices))
    return devices


def fetch_clients(config: Config, *, site: str | None = None) -> Iterable[object]:
    """Fetch active clients from UniFi Controller."""
    try:
        from unifi_controller_api import UnifiAuthenticationError
    except ImportError as exc:
        raise RuntimeError("Missing dependency: unifi-controller-api") from exc

    site_name = site or config.site

    try:
        controller = _init_controller(config, is_udm_pro=True)
    except UnifiAuthenticationError:
        logger.info("UDM Pro authentication failed, retrying legacy auth")
        controller = _init_controller(config, is_udm_pro=False)

    clients = controller.get_unifi_site_client(site_name=site_name, raw=True)
    logger.info("Fetched %d clients", len(clients))
    return clients
