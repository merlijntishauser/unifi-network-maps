import builtins
import sys
from types import SimpleNamespace

import pytest

from unifi_mermaid import unifi
from unifi_mermaid.config import Config


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
