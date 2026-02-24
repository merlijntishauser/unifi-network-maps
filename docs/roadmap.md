# Roadmap

## Inline UniFi client (unifi_api.py)

### Auth response: check HTTP status before parsing JSON
`_validate_auth_response` doesn't check `response.status_code`. If the controller returns HTTP 403 with JSON that happens to contain `"roles"`, auth would silently succeed. Unlikely from a real UniFi controller, but a defensive check would be cleaner.

### Pass request timeout to session calls
`_get()` and `_authenticate()` don't pass `timeout=` to `requests`. Hanging requests are only caught by the outer `_call_with_timeout` ThreadPoolExecutor wrapper in `unifi.py`. Passing timeout natively to `self._session.get()` / `self._session.post()` would give a cleaner abort path.

### Scope SSL warning suppression
`urllib3.disable_warnings()` is process-global. If multiple `UnifiClient` instances exist (some with `verify_ssl=True`, some `False`), warnings stay suppressed for all. Could use a `warnings.catch_warnings()` context or track whether suppression was already applied.

## UniFi adapter (unifi.py)

### Remove redundant serialization layer for devices
`_serialize_device_for_cache` was needed when the upstream returned `UnifiDevice` objects that had to be converted to dicts. Now the inline client always returns `list[dict]`, so this is purely a field-filtering/normalization step. Still useful to avoid caching the full raw response, but the `get_field`/`first_attr` indirection could be simplified to direct `dict.get()` calls.

### Extract generic `_cached_fetch` helper
`fetch_devices`, `fetch_clients`, and `fetch_networks` follow the exact same ~25-line pattern: resolve site, check cache, build closure, call `_connect_and_fetch`, fall back to stale cache, save to cache. The only differences are endpoint method, cache key prefix, and serializer. A generic helper could eliminate the triplication, though the current code is straightforward enough that the duplication is low-cost.
