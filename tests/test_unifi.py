import builtins
import pickle
import sys
import time
from types import SimpleNamespace

import pytest

from unifi_network_maps import unifi
from unifi_network_maps.config import Config


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


def test_fetch_devices_uses_cache(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "3600")

    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    cache_path = tmp_path / f"devices_{unifi._cache_key(config.url, config.site, 'True')}.pkl"
    unifi._save_cache(cache_path, [{"name": "cached"}])

    def fail_init(*_args, **_kwargs):
        raise AssertionError("should not fetch when cache is valid")

    monkeypatch.setattr(unifi, "_init_controller", fail_init)
    devices = list(unifi.fetch_devices(config))
    assert devices[0]["name"] == "cached"


def test_fetch_clients_cache_expired(monkeypatch, tmp_path):
    fake_module = SimpleNamespace(UnifiAuthenticationError=RuntimeError)
    monkeypatch.setitem(sys.modules, "unifi_controller_api", fake_module)
    monkeypatch.setenv("UNIFI_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("UNIFI_CACHE_TTL_SECONDS", "1")

    config = Config(
        url="https://example", site="default", user="user", password="pass", verify_ssl=True
    )
    cache_path = tmp_path / f"clients_{unifi._cache_key(config.url, config.site)}.pkl"
    cache_path.write_bytes(
        pickle.dumps({"timestamp": time.time() - 3600, "data": [{"stale": True}]})
    )

    class Controller:
        def get_unifi_site_client(self, site_name, raw):
            return [{"fresh": True}]

    monkeypatch.setattr(unifi, "_init_controller", lambda *_a, **_k: Controller())
    clients = list(unifi.fetch_clients(config))
    assert clients[0]["fresh"] is True
