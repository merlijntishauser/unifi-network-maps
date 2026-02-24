import pytest
import requests

from unifi_network_maps.adapters.unifi_api import (
    UnifiApiError,
    UnifiAuthError,
    UnifiClient,
)

pytestmark = pytest.mark.unit


class FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, status_code=200, json_data=None, *, ok=True):
        self.status_code = status_code
        self._json_data = json_data
        self.ok = ok

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON")
        return self._json_data


class FakeSession:
    """Captures requests made through a ``requests.Session``."""

    def __init__(self, responses=None):
        self.calls: list[tuple[str, str, dict]] = []
        self._responses = list(responses or [])
        self._index = 0

    def post(self, url, *, json=None, verify=True):
        self.calls.append(("POST", url, {"json": json, "verify": verify}))
        return self._next()

    def get(self, url, *, verify=True):
        self.calls.append(("GET", url, {"verify": verify}))
        return self._next()

    def _next(self):
        resp = self._responses[self._index]
        self._index += 1
        return resp


def _make_client(monkeypatch, session, *, is_udm_pro=False):
    """Construct a ``UnifiClient`` with a pre-built fake session."""
    monkeypatch.setattr(requests, "Session", lambda: session)
    return UnifiClient(
        url="https://unifi.local",
        username="admin",
        password="secret",
        is_udm_pro=is_udm_pro,
        verify_ssl=True,
    )


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------


def test_authenticate_udm_pro(monkeypatch):
    auth_resp = FakeResponse(json_data={"isSuperAdmin": True})
    data_resp = FakeResponse(json_data={"data": [{"name": "switch"}]})
    session = FakeSession([auth_resp, data_resp])
    client = _make_client(monkeypatch, session, is_udm_pro=True)

    assert session.calls[0] == (
        "POST",
        "https://unifi.local/api/auth/login",
        {"json": {"username": "admin", "password": "secret"}, "verify": True},
    )
    assert client._api_base == "https://unifi.local/proxy/network"


def test_authenticate_legacy(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    data_resp = FakeResponse(json_data={"data": []})
    session = FakeSession([auth_resp, data_resp])
    client = _make_client(monkeypatch, session, is_udm_pro=False)

    assert session.calls[0] == (
        "POST",
        "https://unifi.local/api/login",
        {"json": {"username": "admin", "password": "secret"}, "verify": True},
    )
    assert client._api_base == "https://unifi.local"


def test_authenticate_error_payload(monkeypatch):
    error_resp = FakeResponse(
        json_data={"code": "AUTH_FAILED", "message": "Invalid credentials"},
    )
    session = FakeSession([error_resp])
    with pytest.raises(UnifiAuthError, match="AUTH_FAILED"):
        _make_client(monkeypatch, session)


def test_authenticate_unknown_format(monkeypatch):
    odd_resp = FakeResponse(json_data={"something": "unexpected"})
    session = FakeSession([odd_resp])
    with pytest.raises(UnifiAuthError, match="Unknown auth response"):
        _make_client(monkeypatch, session)


def test_authenticate_request_failure(monkeypatch):
    class FailSession:
        def post(self, url, *, json=None, verify=True):
            raise requests.RequestException("connection refused")

    monkeypatch.setattr(requests, "Session", lambda: FailSession())
    with pytest.raises(UnifiAuthError, match="Login request failed"):
        UnifiClient(
            url="https://unifi.local",
            username="admin",
            password="secret",
        )


# ------------------------------------------------------------------
# Data fetching
# ------------------------------------------------------------------


def test_get_devices_url(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    detailed_resp = FakeResponse(json_data={"data": [{"mac": "aa"}]})
    basic_resp = FakeResponse(json_data={"data": [{"mac": "bb"}]})
    session = FakeSession([auth_resp, detailed_resp, basic_resp])
    client = _make_client(monkeypatch, session)

    result = client.get_devices("default", detailed=True)
    assert result == [{"mac": "aa"}]
    assert session.calls[1][1] == "https://unifi.local/api/s/default/stat/device"

    result = client.get_devices("default", detailed=False)
    assert result == [{"mac": "bb"}]
    assert session.calls[2][1] == "https://unifi.local/api/s/default/stat/device-basic"


def test_get_clients_url(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    data_resp = FakeResponse(json_data={"data": [{"mac": "cc"}]})
    session = FakeSession([auth_resp, data_resp])
    client = _make_client(monkeypatch, session)

    result = client.get_clients("mysite")
    assert result == [{"mac": "cc"}]
    assert session.calls[1][1] == "https://unifi.local/api/s/mysite/stat/sta"


def test_get_networkconf_url(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    data_resp = FakeResponse(json_data={"data": [{"_id": "net1"}]})
    session = FakeSession([auth_resp, data_resp])
    client = _make_client(monkeypatch, session)

    result = client.get_networkconf("default")
    assert result == [{"_id": "net1"}]
    assert session.calls[1][1] == "https://unifi.local/api/s/default/rest/networkconf"


def test_reauth_on_401(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    unauthorized = FakeResponse(status_code=401, json_data={}, ok=False)
    reauth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    data_resp = FakeResponse(json_data={"data": [{"ok": True}]})
    session = FakeSession([auth_resp, unauthorized, reauth_resp, data_resp])
    client = _make_client(monkeypatch, session)

    result = client.get_clients("default")
    assert result == [{"ok": True}]
    # calls: initial auth POST, GET (401), re-auth POST, GET (success)
    assert len(session.calls) == 4
    assert session.calls[2][0] == "POST"


def test_parse_data_field(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    data_resp = FakeResponse(json_data={"data": [{"a": 1}, {"b": 2}]})
    session = FakeSession([auth_resp, data_resp])
    client = _make_client(monkeypatch, session)

    result = client.get_clients("default")
    assert len(result) == 2
    assert result[0] == {"a": 1}


def test_missing_data_field(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    bad_resp = FakeResponse(json_data={"result": "wrong"})
    session = FakeSession([auth_resp, bad_resp])
    client = _make_client(monkeypatch, session)

    with pytest.raises(UnifiApiError, match="Missing 'data' field"):
        client.get_clients("default")


def test_get_http_error(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    error_resp = FakeResponse(status_code=500, json_data={}, ok=False)
    session = FakeSession([auth_resp, error_resp])
    client = _make_client(monkeypatch, session)

    with pytest.raises(UnifiApiError, match="failed \\(HTTP 500\\)"):
        client.get_devices("default")


def test_get_non_json_response(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    html_resp = FakeResponse(status_code=200, json_data=None, ok=True)
    session = FakeSession([auth_resp, html_resp])
    client = _make_client(monkeypatch, session)

    with pytest.raises(UnifiApiError, match="Non-JSON response"):
        client.get_clients("default")


def test_reauth_succeeds_but_retry_fails(monkeypatch):
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    unauthorized = FakeResponse(status_code=401, json_data={}, ok=False)
    reauth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    forbidden = FakeResponse(status_code=403, json_data={}, ok=False)
    session = FakeSession([auth_resp, unauthorized, reauth_resp, forbidden])
    client = _make_client(monkeypatch, session)

    with pytest.raises(UnifiApiError, match="failed \\(HTTP 403\\)"):
        client.get_clients("default")


def test_ssl_warning_suppressed(monkeypatch):
    calls = []
    monkeypatch.setattr("urllib3.disable_warnings", lambda *a: calls.append(a))
    auth_resp = FakeResponse(json_data={"meta": {"rc": "ok"}})
    session = FakeSession([auth_resp])
    monkeypatch.setattr(requests, "Session", lambda: session)

    UnifiClient(
        url="https://unifi.local",
        username="admin",
        password="secret",
        verify_ssl=False,
    )
    assert len(calls) == 1
