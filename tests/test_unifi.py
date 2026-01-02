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
