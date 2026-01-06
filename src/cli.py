"""Backward-compatible CLI module wrapper."""  # pragma: no cover

from __future__ import annotations

from unifi_network_maps.cli import main  # pragma: no cover

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())  # pragma: no cover
