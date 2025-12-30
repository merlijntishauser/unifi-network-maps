"""Backward-compatible CLI module wrapper."""

from __future__ import annotations

from unifi_mermaid.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
