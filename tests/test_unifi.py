import builtins
import json
import os
import sys
import time
from types import SimpleNamespace

import pytest

from unifi_network_maps.adapters import unifi
from unifi_network_maps.adapters.config import Config


def test_fetch_devices_falls_back_on_auth_error(monkeypatch):
    class FakeAuthError(Exception):
        pass

    fake_module = SimpleNamespace(UnifiAuthenticationError=FakeAuthError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)

    def fake_init_controller(config, *, is_udm_pro):
        if is_udm_pro:
            raise FakeAuthError("bad auth")

        class Controller:
            def get_unifi_site_device(self, site_name, detailed, raw):
                return [object(), object()]

        return Controller()

    monkeypatch.setattr(unifi, "_init_controller", fake_init_controller)
    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    devices = list(unifi.fetch_devices(config))
    assert len(devices) == 2


def test_fetch_devices_requires_dependency(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "unifi_controller_api":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    with pytest.raises(RuntimeError) as excinfo:
        unifi.fetch_devices(config)
    assert "Missing dependency" in str(excinfo.value)


def test_init_controller_passes_config(monkeypatch):
    captured = {}

    class FakeController:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_module = SimpleNamespace(UnifiController=FakeController)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=False
    )
    unifi._init_controller(config, is_udm_pro=True)
    assert captured["verify_ssl"] is False


def test_fetch_clients_falls_back_on_auth_error(monkeypatch):
    class FakeAuthError(Exception):
        pass

    fake_module = SimpleNamespace(UnifiAuthenticationError=FakeAuthError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)

    def fake_init_controller(config, *, is_udm_pro):
        if is_udm_pro:
            raise FakeAuthError("bad auth")

        class Controller:
            def get_unifi_site_client(self, site_name, raw):
                return [object()]

        return Controller()

    monkeypatch.setattr(unifi, "_init_controller", fake_init_controller)
    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    clients = list(unifi.fetch_clients(config))
    assert len(clients) == 1


def test_fetch_clients_requires_dependency(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "unifi_controller_api":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    with pytest.raises(RuntimeError) as excinfo:
        unifi.fetch_clients(config)
    assert "Missing dependency" in str(excinfo.value)


def test_cache_dir_rejects_symlink(monkeypatch, tmp_path):
    if not hasattr(os, "symlink"):
        pytest.skip("OS does not support symlinks")
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link_dir = tmp_path / "link"
    os.symlink(real_dir, link_dir)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(link_dir))
    cache_dir = unifi._cache_dir()
    assert cache_dir != link_dir
    assert not cache_dir.is_symlink()


def test_fetch_devices_uses_cache(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "3600")

    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    cache_path = tmp_path / f"devices_{unifi._cache_key(config.url, config.site, 'True')}.json"
    unifi._save_cache(cache_path, [{"name": "cached"}])

    def fail_init(*_args, **_kwargs):
        raise AssertionError("should not fetch when cache is valid")

    monkeypatch.setattr(unifi, "_init_controller", fail_init)
    devices = list(unifi.fetch_devices(config))
    device = devices[0]
    assert isinstance(device, dict)
    assert device["name"] == "cached"


def test_fetch_devices_skips_cache_when_disabled(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "3600")

    cache_path = tmp_path / f"devices_{unifi._cache_key('url', 'default', 'True')}.json"
    cache_path.write_text(
        json.dumps({"timestamp": time.time(), "data": [{"name": "cached"}]}),
        encoding="utf-8",
    )

    calls = {"count": 0}

    class Controller:
        def get_unifi_site_device(self, site_name, detailed, raw):
            calls["count"] += 1
            return [{"name": "fresh"}]

    monkeypatch.setattr(unifi, "_init_controller", lambda *_a, **_k: Controller())
    config = Config(url="url", site="default", user="user", password="pass", verify_ssl=True)
    devices = list(unifi.fetch_devices(config, use_cache=False))
    device = devices[0]
    assert calls["count"] == 1
    assert isinstance(device, dict)
    assert device["name"] == "fresh"


def test_fetch_clients_cache_expired(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "1")

    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    cache_path = tmp_path / f"clients_{unifi._cache_key(config.url, config.site)}.json"
    cache_path.write_text(
        json.dumps({"timestamp": time.time() - 3600, "data": [{"stale": True}]}),
        encoding="utf-8",
    )

    class Controller:
        def get_unifi_site_client(self, site_name, raw):
            return [{"fresh": True}]

    monkeypatch.setattr(unifi, "_init_controller", lambda *_a, **_k: Controller())
    clients = list(unifi.fetch_clients(config))
    client = clients[0]
    assert isinstance(client, dict)
    assert client["fresh"] is True


def test_fetch_devices_uses_stale_cache_on_error(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "1")

    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    cache_path = tmp_path / f"devices_{unifi._cache_key(config.url, config.site, 'True')}.json"
    cache_path.write_text(
        json.dumps({"timestamp": time.time() - 3600, "data": [{"stale": True}]}),
        encoding="utf-8",
    )

    class Controller:
        def get_unifi_site_device(self, site_name, detailed, raw):
            raise RuntimeError("boom")

    monkeypatch.setattr(unifi, "_init_controller", lambda *_a, **_k: Controller())
    devices = list(unifi.fetch_devices(config))
    device = devices[0]
    assert isinstance(device, dict)
    assert device["stale"] is True


def test_fetch_clients_uses_stale_cache_on_error(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "1")

    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    cache_path = tmp_path / f"clients_{unifi._cache_key(config.url, config.site)}.json"
    cache_path.write_text(
        json.dumps({"timestamp": time.time() - 3600, "data": [{"stale": True}]}),
        encoding="utf-8",
    )

    class Controller:
        def get_unifi_site_client(self, site_name, raw):
            raise RuntimeError("boom")

    monkeypatch.setattr(unifi, "_init_controller", lambda *_a, **_k: Controller())
    clients = list(unifi.fetch_clients(config))
    client = clients[0]
    assert isinstance(client, dict)
    assert client["stale"] is True


def test_fetch_devices_retries(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_RETRY_ATTEMPTS", "2")
    monkeypatch.setenv("UNIFI_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "0")
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))

    calls = {"count": 0}

    class Controller:
        def get_unifi_site_device(self, site_name, detailed, raw):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("boom")
            return [{"ok": True}]

    monkeypatch.setattr(unifi, "_init_controller", lambda *_a, **_k: Controller())
    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    devices = list(unifi.fetch_devices(config))
    assert calls["count"] == 2
    device = devices[0]
    assert isinstance(device, dict)
    assert device["ok"] is True


def test_call_with_retries_times_out(monkeypatch):
    monkeypatch.setenv("UNIFI_RETRY_ATTEMPTS", "1")
    monkeypatch.setenv("UNIFI_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("UNIFI_REQUEST_TIMEOUT_SECONDS", "0.01")

    def slow_call():
        time.sleep(0.05)
        return "ok"

    with pytest.raises(TimeoutError):
        unifi._call_with_retries("slow", slow_call)


def test_fetch_devices_skips_cache_when_dir_is_world_writable(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "3600")

    cache_path = tmp_path / f"devices_{unifi._cache_key('url', 'default', 'True')}.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"timestamp": time.time(), "data": [{"name": "cached"}]}),
        encoding="utf-8",
    )
    tmp_path.chmod(0o777)

    called = {"count": 0}

    class Controller:
        def get_unifi_site_device(self, site_name, detailed, raw):
            called["count"] += 1
            return [{"name": "fresh"}]

    monkeypatch.setattr(unifi, "_init_controller", lambda *_a, **_k: Controller())
    config = Config(url="url", site="default", user="user", password="pass", verify_ssl=True)
    devices = list(unifi.fetch_devices(config))
    device = devices[0]
    assert called["count"] == 1
    assert isinstance(device, dict)
    assert device["name"] == "fresh"


def test_load_cache_with_age_requires_dict_payload(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
    data, age = unifi._load_cache_with_age(cache_path)
    assert data is None
    assert age is None


def test_load_cache_with_age_requires_timestamp(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps({"data": []}), encoding="utf-8")
    data, age = unifi._load_cache_with_age(cache_path)
    assert data is None
    assert age is None


def test_load_cache_with_age_requires_list_data(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps({"timestamp": time.time(), "data": {}}), encoding="utf-8")
    data, age = unifi._load_cache_with_age(cache_path)
    assert data is None
    assert age is None


def test_load_cache_respects_ttl(monkeypatch, tmp_path):
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        json.dumps({"timestamp": time.time() - 10, "data": [{"ok": True}]}),
        encoding="utf-8",
    )
    assert unifi._load_cache(cache_path, ttl_seconds=0) is None
    assert unifi._load_cache(cache_path, ttl_seconds=1) is None


def test_cache_ttl_seconds_invalid_uses_default(monkeypatch):
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "nope")
    assert unifi._cache_ttl_seconds() == 3600


def test_retry_attempts_invalid_uses_default(monkeypatch):
    monkeypatch.setenv("UNIFI_RETRY_ATTEMPTS", "nope")
    assert unifi._retry_attempts() == 2


def test_retry_backoff_invalid_uses_default(monkeypatch):
    monkeypatch.setenv("UNIFI_RETRY_BACKOFF_SECONDS", "nope")
    assert unifi._retry_backoff_seconds() == 0.5


def test_request_timeout_invalid_returns_none(monkeypatch):
    monkeypatch.setenv("UNIFI_REQUEST_TIMEOUT_SECONDS", "nope")
    assert unifi._request_timeout_seconds() is None


def test_serialize_lldp_entries_filters_missing_fields():
    class Entry:
        def __init__(self, chassis_id=None, port_id=None):
            self.chassis_id = chassis_id
            self.port_id = port_id

    entries = [Entry(chassis_id="aa", port_id="1"), Entry(chassis_id="bb")]
    serialized = unifi._serialize_lldp_entries(entries)
    assert len(serialized) == 1
    assert serialized[0]["chassis_id"] == "aa"


def test_serialize_lldp_entries_accepts_single_object():
    entry = {"chassis_id": "aa", "port_id": "1"}
    serialized = unifi._serialize_lldp_entries(entry)
    assert serialized[0]["port_id"] == "1"


def test_serialize_uplink_returns_none_when_empty():
    assert unifi._serialize_uplink({"uplink_mac": None, "uplink_device_name": None}) is None


def test_serialize_uplink_reads_fallback_fields():
    data = unifi._serialize_uplink(
        {"uplink_device_mac": "aa", "uplink_name": "Core", "port_idx": 3}
    )
    assert data == {"uplink_mac": "aa", "uplink_device_name": "Core", "uplink_remote_port": 3}


def test_serialize_port_entry_reads_aggregation_group():
    data = unifi._serialize_port_entry({"port_idx": 1, "agg_id": "agg2"})
    assert data["aggregation_group"] == "agg2"
