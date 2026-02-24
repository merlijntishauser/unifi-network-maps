# Plan: Replace unifi-controller-api with inline thin client

## Context

`unifi-network-maps` (v1.6.4, 560 commits, 43 test files) depends on `unifi-controller-api` (v0.3.2, 42 commits, 0 tests) for UniFi controller access. Analysis shows the upstream provides ~300 lines of actual value out of 5,772: authentication, session management, and HTTP transport for just 3 GET endpoints. The project already distrusts the upstream's models (`raw=True` for 2/3 calls) and does all data normalization itself.

This plan replaces the external dependency with an inline ~120-line client module. The change is invisible to all public API consumers.

## Step 1: Create `src/unifi_network_maps/adapters/unifi_api.py`

New file (~120 lines). Provides `UnifiAuthError`, `UnifiApiError`, and `UnifiClient`.

```python
class UnifiAuthError(Exception): ...
class UnifiApiError(Exception): ...

class UnifiClient:
    def __init__(self, url, username, password, *, is_udm_pro=False, verify_ssl=True): ...
    def _authenticate(self) -> None: ...
    def _validate_auth_response(self, response) -> None: ...
    def _get(self, path) -> list[dict[str, object]]: ...
    def get_devices(self, site, *, detailed=False) -> list[dict[str, object]]: ...
    def get_clients(self, site) -> list[dict[str, object]]: ...
    def get_networkconf(self, site) -> list[dict[str, object]]: ...
```

Key design decisions:
- Uses `requests.Session()` for persistent cookies (same as upstream)
- Dual auth: UDM Pro POSTs to `/api/auth/login` then prefixes `/proxy/network`; legacy POSTs to `/api/login`
- Validates response: checks `meta.rc == "ok"` (legacy) or `isSuperAdmin`/`roles` (UniFi OS), detects error payloads (HTTP 200 with `code` + `message`)
- Single 401 re-auth retry in `_get()` (outer `_call_with_retries` handles multi-attempt)
- No CSRF token handling needed (only GET requests)
- Suppresses `InsecureRequestWarning` when `verify_ssl=False`
- All methods return `list[dict]` -- no model parsing
- Response parsing: extracts `data` from `{"data": [...]}`

## Step 2: Update `src/unifi_network_maps/adapters/unifi.py`

Surgical changes, ~20 lines modified:

**Imports:** Replace `TYPE_CHECKING` + conditional `UnifiController` import with direct import of `UnifiAuthError` and `UnifiClient` from `.unifi_api`

**`_init_controller` -> `_create_client`:** Rename function, change return type to `UnifiClient`, update constructor args (`controller_url` -> `url`, `username` -> `username`, etc.)

**`_connect_and_fetch`:** Replace `UnifiAuthenticationError` with `UnifiAuthError`, `_init_controller` with `_create_client`, update type annotation from `UnifiController` to `UnifiClient`

**`fetch_devices`:** Remove `import unifi_controller_api` guard. Change `ctrl.get_unifi_site_device(site_name=site_name, detailed=detailed, raw=False)` to `client.get_devices(site_name, detailed=detailed)`. Since the inline client always returns dicts, the serialization step `_serialize_devices_for_cache(devices)` still works because `_serialize_device_for_cache` uses `get_field()` which handles both dicts and objects.

**`fetch_clients`:** Remove import guard. Change `ctrl.get_unifi_site_client(site_name=site_name, raw=True)` to `client.get_clients(site_name)`

**`fetch_networks`:** Remove import guard. Change `ctrl.get_unifi_site_networkconf(site_name=site_name, raw=True)` to `client.get_networkconf(site_name)`

Everything else (caching, retry, serialization, `fetch_payload`) stays identical.

## Step 3: Update `pyproject.toml`

- Remove: `"unifi-controller-api==0.3.2"`
- Add: `"requests>=2.31,<3"`

## Step 4: Update `src/unifi_network_maps/cli/main.py`

Remove the `_DowngradeInfoToDebugFilter` class and its application in `main()`. This filter silenced verbose INFO logs from the `unifi_controller_api` logger namespace. The inline client logs under `unifi_network_maps.adapters.unifi_api` which is already under the project namespace and controlled by the existing log level configuration.

## Step 5: Create `tests/test_unifi_api.py`

New test file for the inline client. Uses monkeypatched `requests.Session` to avoid real HTTP calls. Tests:

- `test_authenticate_udm_pro` -- verifies POST to `/api/auth/login`, `_api_base` set to `/proxy/network`
- `test_authenticate_legacy` -- verifies POST to `/api/login`
- `test_authenticate_error_payload` -- HTTP 200 with error JSON raises `UnifiAuthError`
- `test_authenticate_unknown_format` -- unknown response raises `UnifiAuthError`
- `test_authenticate_request_failure` -- `RequestException` wrapped as `UnifiAuthError`
- `test_get_devices_url` -- correct URL construction for both detailed and basic
- `test_get_clients_url` -- correct URL for `/stat/sta`
- `test_get_networkconf_url` -- correct URL for `/rest/networkconf`
- `test_reauth_on_401` -- 401 triggers re-auth then retry
- `test_parse_data_field` -- extracts `data` from response
- `test_missing_data_field` -- raises `UnifiApiError`
- `test_ssl_warning_suppressed` -- `urllib3.disable_warnings` called when `verify_ssl=False`

## Step 6: Migrate `tests/test_unifi.py`

Systematic changes across all test functions:

| Pattern | Before | After |
|---------|--------|-------|
| Import fake auth | `class FakeAuthError(Exception)` | `from unifi_network_maps.adapters.unifi_api import UnifiAuthError` |
| Fake module injection | `monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)` | Remove entirely |
| Factory monkeypatch | `monkeypatch.setattr(unifi, "_init_controller", ...)` | `monkeypatch.setattr(unifi, "_create_client", ...)` |
| Fake controller methods | `get_unifi_site_device(self, site_name, detailed, raw)` | `get_devices(self, site, *, detailed)` |
| | `get_unifi_site_client(self, site_name, raw)` | `get_clients(self, site)` |
| | `get_unifi_site_networkconf(self, site_name, raw)` | `get_networkconf(self, site)` |

Tests to **delete**: `test_fetch_devices_requires_dependency`, `test_fetch_clients_requires_dependency` (the import guard no longer exists since the client is inline).

Tests that need **no changes**: all cache utility tests, serialization tests, `test_is_rate_limited_detects_429`, `test_call_with_retries_times_out`.

## Step 7: Update documentation references

- `CLAUDE.md`: Update dependency reference from `unifi-controller-api` to `requests`
- `AGENTS.md`: Remove or update the `### UniFi API` section
- `CHANGELOG.md`: Add entry documenting the replacement

## Verification

```bash
ruff check src/unifi_network_maps/adapters/unifi_api.py src/unifi_network_maps/adapters/unifi.py
pyright src/ tests/
radon cc src/unifi_network_maps/adapters/unifi_api.py -a -s  # all <= C, avg <= A
pytest tests/test_unifi.py tests/test_unifi_api.py -v
pytest  # full suite
grep -r "unifi_controller_api\|unifi-controller-api" src/ tests/ pyproject.toml  # should be empty
pip install -e .  # should not pull unifi-controller-api
```

## Files to modify

| File | Action |
|------|--------|
| `src/unifi_network_maps/adapters/unifi_api.py` | **Create** -- inline thin client |
| `src/unifi_network_maps/adapters/unifi.py` | **Edit** -- swap imports, rename factory, update 3 fetch functions |
| `pyproject.toml` | **Edit** -- swap dependency |
| `src/unifi_network_maps/cli/main.py` | **Edit** -- remove logging filter |
| `tests/test_unifi_api.py` | **Create** -- tests for inline client |
| `tests/test_unifi.py` | **Edit** -- migrate mocks, delete 2 obsolete tests |
| `CLAUDE.md`, `AGENTS.md` | **Edit** -- update references |
| `CHANGELOG.md` | **Edit** -- add entry |
