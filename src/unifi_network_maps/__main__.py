"""Module entrypoint for python -m unifi_network_maps."""

from __future__ import annotations

from .cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
