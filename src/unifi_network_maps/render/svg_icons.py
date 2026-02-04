"""Icon loading and color management for SVG rendering."""

from __future__ import annotations

import base64
from pathlib import Path

from .svg_theme import SvgTheme

# Icon file mappings per icon set
# Isometric set uses existing icons from root and isometric/ directories
# New device types fall back to generic icons in isometric set
_ICON_FILES_ISOMETRIC = {
    "gateway": "router-network.svg",
    "switch": "server-network.svg",
    "ap": "access-point.svg",
    "camera": "laptop.svg",
    "tv": "laptop.svg",
    "phone": "laptop.svg",
    "printer": "laptop.svg",
    "nas": "server.svg",
    "speaker": "laptop.svg",
    "game_console": "laptop.svg",
    "iot": "server.svg",
    "client": "laptop.svg",
    "client_cluster": "laptop.svg",
    "other": "server.svg",
}

_ISO_ICON_FILES_ISOMETRIC = {
    "gateway": "router.svg",
    "switch": "switch-module.svg",
    "ap": "tower.svg",
    "camera": "laptop.svg",
    "tv": "laptop.svg",
    "phone": "laptop.svg",
    "printer": "laptop.svg",
    "nas": "server.svg",
    "speaker": "laptop.svg",
    "game_console": "laptop.svg",
    "iot": "server.svg",
    "client": "laptop.svg",
    "client_cluster": "laptop.svg",
    "other": "server.svg",
}

# Modern set uses consistent naming in modern/ directory
_ICON_FILES_MODERN = {
    "gateway": "gateway.svg",
    "switch": "switch.svg",
    "ap": "ap.svg",
    "camera": "camera.svg",
    "tv": "tv.svg",
    "phone": "phone.svg",
    "printer": "printer.svg",
    "nas": "nas.svg",
    "speaker": "speaker.svg",
    "game_console": "game_console.svg",
    "iot": "iot.svg",
    "client": "client.svg",
    "client_cluster": "client.svg",
    "other": "other.svg",
}

# Icon set registry: maps set names to (flat_dir, iso_dir, flat_files, iso_files)
_ICON_SETS = {
    "isometric": (
        "",  # Flat icons in root icons/ directory
        "isometric",  # Isometric icons in isometric/ subdirectory
        _ICON_FILES_ISOMETRIC,
        _ISO_ICON_FILES_ISOMETRIC,
    ),
    "modern": (
        "modern-flat",  # Flat icons for orthogonal SVG
        "modern",  # Isometric icons for iso SVG
        _ICON_FILES_MODERN,
        _ICON_FILES_MODERN,
    ),
}

# Node type fill/stroke colors for orthogonal rendering
_TYPE_COLORS = {
    "gateway": ("#ffd199", "#f08a00"),
    "switch": ("#bfe4ff", "#1c6dd0"),
    "ap": ("#c4f2d4", "#1f9a50"),
    "camera": ("#b3e5fc", "#0277bd"),
    "tv": ("#d1c4e9", "#512da8"),
    "phone": ("#c8e6c9", "#388e3c"),
    "printer": ("#cfd8dc", "#546e7a"),
    "nas": ("#ffe0b2", "#e65100"),
    "speaker": ("#b2dfdb", "#00796b"),
    "game_console": ("#e1bee7", "#7b1fa2"),
    "iot": ("#b2ebf2", "#00838f"),
    "client": ("#e4ccff", "#6b2fb4"),
    "client_cluster": ("#d4b8ff", "#5a25a0"),
    "other": ("#e3e3e3", "#7b7b7b"),
}

# Type ordering for layout sorting
_TYPE_ORDER = [
    "gateway",
    "switch",
    "ap",
    "camera",
    "tv",
    "phone",
    "printer",
    "nas",
    "speaker",
    "game_console",
    "iot",
    "client",
    "client_cluster",
    "other",
]


def _darken_hex(color: str, factor: float = 0.35) -> str:
    """Darken a hex color by *factor* (0..1). Returns 6-digit hex."""
    c = color.lstrip("#")
    if len(c) != 6:
        return color
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    m = 1.0 - factor
    return f"#{int(r * m):02x}{int(g * m):02x}{int(b * m):02x}"


def _build_decal_colors(theme: SvgTheme, factor: float = 0.35) -> dict[str, str]:
    """Derive per-type icon decal colors by darkening each node's gradient end."""
    node_attrs = {
        "gateway": theme.node_gateway,
        "switch": theme.node_switch,
        "ap": theme.node_ap,
        "client": theme.node_client,
        "other": theme.node_other,
        "camera": theme.node_camera,
        "tv": theme.node_tv,
        "phone": theme.node_phone,
        "printer": theme.node_printer,
        "nas": theme.node_nas,
        "speaker": theme.node_speaker,
        "game_console": theme.node_game_console,
        "iot": theme.node_iot,
        "client_cluster": theme.node_client_cluster,
    }
    return {name: _darken_hex(pair[1], factor) for name, pair in node_attrs.items()}


def _load_icons(icon_set: str = "isometric", decal_color: str = "#1a1a1a") -> dict[str, str]:
    """Load flat (non-isometric) icons for the specified icon set.

    Falls back to isometric icons if the requested icon is not found in the set.
    Modern icons use #DECAL0 as placeholder which gets replaced with decal_color.
    """
    base = Path(__file__).resolve().parents[1] / "assets" / "icons"
    icons: dict[str, str] = {}

    set_config = _ICON_SETS.get(icon_set, _ICON_SETS["isometric"])
    subdir, _, file_map, _ = set_config

    fallback_config = _ICON_SETS["isometric"]
    fallback_subdir, _, fallback_files, _ = fallback_config

    for node_type in _ICON_FILES_ISOMETRIC.keys():
        filename = file_map.get(node_type)
        if filename:
            path = base / subdir / filename if subdir else base / filename
            if path.exists():
                data = path.read_text(encoding="utf-8")
                data = data.replace("#DECAL0", decal_color)
                encoded = base64.b64encode(data.encode("utf-8")).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"
                continue

        fallback_filename = fallback_files.get(node_type)
        if fallback_filename:
            fallback_path = (
                base / fallback_subdir / fallback_filename
                if fallback_subdir
                else base / fallback_filename
            )
            if fallback_path.exists():
                data = fallback_path.read_bytes()
                encoded = base64.b64encode(data).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"

    return icons


def _load_isometric_icons(
    icon_set: str = "isometric",
    decal_color: str = "#5A6878",
    decal_colors: dict[str, str] | None = None,
) -> dict[str, str]:
    """Load isometric icons for the specified icon set.

    Falls back to isometric icons if the requested icon is not found in the set.
    Modern icons use #DECAL0 as placeholder which gets replaced with a per-type
    color from *decal_colors* (falling back to *decal_color*).
    """
    base = Path(__file__).resolve().parents[1] / "assets" / "icons"
    icons: dict[str, str] = {}

    set_config = _ICON_SETS.get(icon_set, _ICON_SETS["isometric"])
    _, iso_subdir, _, iso_file_map = set_config

    fallback_config = _ICON_SETS["isometric"]
    _, fallback_iso_subdir, _, fallback_iso_files = fallback_config

    for node_type in _ISO_ICON_FILES_ISOMETRIC.keys():
        filename = iso_file_map.get(node_type)
        if filename:
            path = base / iso_subdir / filename
            if path.exists():
                content = path.read_text(encoding="utf-8")
                color = decal_colors.get(node_type, decal_color) if decal_colors else decal_color
                content = content.replace("#DECAL0", color)
                data = content.encode("utf-8")
                encoded = base64.b64encode(data).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"
                continue

        fallback_filename = fallback_iso_files.get(node_type)
        if fallback_filename:
            fallback_path = base / fallback_iso_subdir / fallback_filename
            if fallback_path.exists():
                data = fallback_path.read_bytes()
                encoded = base64.b64encode(data).decode("ascii")
                icons[node_type] = f"data:image/svg+xml;base64,{encoded}"

    return icons
