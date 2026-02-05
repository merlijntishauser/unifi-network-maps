from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

for name in list(sys.modules):
    if name == "unifi_network_maps" or name.startswith("unifi_network_maps."):
        del sys.modules[name]


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom pytest options."""
    parser.addoption(
        "--update-baselines",
        action="store_true",
        default=False,
        help="Update visual regression baseline images instead of comparing",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically mark tests without specific markers as unit tests."""
    specific_markers = {"integration", "contract", "acceptance"}
    for item in items:
        item_markers = {marker.name for marker in item.iter_markers()}
        if not item_markers & specific_markers:
            item.add_marker(pytest.mark.unit)
