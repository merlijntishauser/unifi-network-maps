import pytest

from unifi_mermaid.config import Config, _parse_bool


def test_parse_bool_true_default():
    assert _parse_bool(None, default=True) is True


def test_parse_bool_false():
    assert _parse_bool("false", default=True) is False


def test_parse_bool_unknown_uses_default():
    assert _parse_bool("maybe", default=False) is False


def test_config_from_env_missing_url(monkeypatch):
    monkeypatch.setenv("UNIFI_URL", "")
    monkeypatch.setenv("UNIFI_USER", "user")
    monkeypatch.setenv("UNIFI_PASS", "pass")
    with pytest.raises(ValueError) as excinfo:
        Config.from_env()
    assert "UNIFI_URL is required" in str(excinfo.value)


def test_config_from_env_missing_user(monkeypatch):
    monkeypatch.setenv("UNIFI_URL", "https://example.local")
    monkeypatch.setenv("UNIFI_USER", "")
    monkeypatch.setenv("UNIFI_PASS", "pass")
    with pytest.raises(ValueError) as excinfo:
        Config.from_env()
    assert "UNIFI_USER is required" in str(excinfo.value)


def test_config_from_env_missing_password(monkeypatch):
    monkeypatch.setenv("UNIFI_URL", "https://example.local")
    monkeypatch.setenv("UNIFI_USER", "user")
    monkeypatch.setenv("UNIFI_PASS", "")
    with pytest.raises(ValueError) as excinfo:
        Config.from_env()
    assert "UNIFI_PASS is required" in str(excinfo.value)


def test_config_from_env_success(monkeypatch):
    monkeypatch.setenv("UNIFI_URL", "https://example.local")
    monkeypatch.setenv("UNIFI_SITE", "default")
    monkeypatch.setenv("UNIFI_USER", "user")
    monkeypatch.setenv("UNIFI_PASS", "pass")
    monkeypatch.setenv("UNIFI_VERIFY_SSL", "false")
    config = Config.from_env()
    assert config.verify_ssl is False
