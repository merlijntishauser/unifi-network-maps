"""Configuration loading from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..io.paths import resolve_env_file


def _parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


@dataclass(frozen=True)
class Config:
    url: str
    site: str
    user: str
    password: str
    verify_ssl: bool

    @classmethod
    def from_env(cls, *, env_file: str | Path | None = None) -> Config:
        if env_file:
            try:
                from dotenv import load_dotenv
            except ImportError:
                raise ValueError("python-dotenv required for --env-file") from None
            env_path = resolve_env_file(env_file)
            load_dotenv(dotenv_path=env_path)
        url = os.environ.get("UNIFI_URL", "").strip()
        site = os.environ.get("UNIFI_SITE", "default").strip()
        user = os.environ.get("UNIFI_USER", "").strip()
        password = os.environ.get("UNIFI_PASS", "").strip()
        verify_ssl = _parse_bool(os.environ.get("UNIFI_VERIFY_SSL"), default=True)

        if not url:
            raise ValueError("UNIFI_URL is required")
        if not user:
            raise ValueError("UNIFI_USER is required")
        if not password:
            raise ValueError("UNIFI_PASS is required")

        return cls(url=url, site=site, user=user, password=password, verify_ssl=verify_ssl)
