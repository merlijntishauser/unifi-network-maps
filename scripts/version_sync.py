#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(r'^version\s*=\s*"[^"]+"', f'version = "{version}"', text, flags=re.M)
    pyproject.write_text(text, encoding="utf-8")
    (ROOT / "src" / "unifi_network_maps" / "__init__.py").write_text(
        f'__version__ = "{version}"\n', encoding="utf-8"
    )


if __name__ == "__main__":
    main()
