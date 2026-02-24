"""Thin UniFi controller HTTP client.

Replaces the ``unifi-controller-api`` external dependency with ~120 lines
of code covering the three GET endpoints this project actually uses.
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)


class UnifiAuthError(Exception):
    """Authentication with the UniFi controller failed."""


class UnifiApiError(Exception):
    """An API request to the UniFi controller failed."""


class UnifiClient:
    """Minimal UniFi controller client.

    Supports both UDM Pro (UniFi OS) and legacy controller authentication.
    All data methods return ``list[dict[str, object]]``.
    """

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        *,
        is_udm_pro: bool = False,
        verify_ssl: bool = True,
    ) -> None:
        self._url = url.rstrip("/")
        self._username = username
        self._password = password
        self._is_udm_pro = is_udm_pro
        self._verify_ssl = verify_ssl
        self._api_base = f"{self._url}/proxy/network" if is_udm_pro else self._url
        self._session = requests.Session()

        if not verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self._authenticate()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _authenticate(self) -> None:
        login_path = "/api/auth/login" if self._is_udm_pro else "/api/login"
        login_url = f"{self._url}{login_path}"
        try:
            response = self._session.post(
                login_url,
                json={"username": self._username, "password": self._password},
                verify=self._verify_ssl,
            )
        except requests.RequestException as exc:
            raise UnifiAuthError(f"Login request failed: {exc}") from exc
        self._validate_auth_response(response)

    def _validate_auth_response(self, response: requests.Response) -> None:
        try:
            data = response.json()
        except ValueError as exc:
            raise UnifiAuthError(f"Non-JSON auth response (HTTP {response.status_code})") from exc

        # Error payload: HTTP 200 with {"code": ..., "message": ...}
        if isinstance(data, dict) and "code" in data and "message" in data and "meta" not in data:
            raise UnifiAuthError(f"{data['code']}: {data['message']}")

        # Legacy: {"meta": {"rc": "ok"}, ...}
        meta = data.get("meta", {}) if isinstance(data, dict) else {}
        if isinstance(meta, dict) and meta.get("rc") == "ok":
            return

        # UniFi OS: {"isSuperAdmin": true, ...} or {"roles": [...], ...}
        if isinstance(data, dict) and ("isSuperAdmin" in data or "roles" in data):
            return

        raise UnifiAuthError(f"Unknown auth response format (HTTP {response.status_code})")

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _get(self, path: str) -> list[dict[str, object]]:
        url = f"{self._api_base}{path}"
        response = self._session.get(url, verify=self._verify_ssl)

        if response.status_code == 401:
            logger.debug("Got 401, re-authenticating")
            self._authenticate()
            response = self._session.get(url, verify=self._verify_ssl)

        if not response.ok:
            raise UnifiApiError(f"GET {path} failed (HTTP {response.status_code})")

        try:
            payload = response.json()
        except ValueError as exc:
            raise UnifiApiError(f"Non-JSON response for {path}") from exc

        if not isinstance(payload, dict) or "data" not in payload:
            raise UnifiApiError(f"Missing 'data' field in response for {path}")

        return payload["data"]

    def get_devices(self, site: str, *, detailed: bool = False) -> list[dict[str, object]]:
        endpoint = "stat/device" if detailed else "stat/device-basic"
        return self._get(f"/api/s/{site}/{endpoint}")

    def get_clients(self, site: str) -> list[dict[str, object]]:
        return self._get(f"/api/s/{site}/stat/sta")

    def get_networkconf(self, site: str) -> list[dict[str, object]]:
        return self._get(f"/api/s/{site}/rest/networkconf")
