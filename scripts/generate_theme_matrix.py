#!/usr/bin/env python3
"""Generate a composite theme x icon-set matrix image.

Produces 20 individual SVGs (5 themes x 2 icon sets x 2 formats) and
assembles them into a single labeled PNG grid at
examples/themes/theme_matrix.png.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "examples" / "themes"
MOCK_DATA = OUTPUT_DIR / "theme_mock_data.json"

# Mock data generation settings for a more complex network
MOCK_SEED = 42
MOCK_SWITCHES = 3
MOCK_APS = 2
MOCK_WIRED_CLIENTS = 4
MOCK_WIRELESS_CLIENTS = 3

THEMES = ["unifi", "unifi-dark", "minimal", "classic", "classic-dark"]
ICON_SETS = ["isometric", "modern"]
FORMATS = ["svg", "svg-iso"]

THEME_LABELS = {
    "unifi": "UniFi",
    "unifi-dark": "UniFi Dark",
    "minimal": "Minimal",
    "classic": "Classic",
    "classic-dark": "Classic Dark",
}

FORMAT_LABELS = {
    "svg": "Orthogonal (svg)",
    "svg-iso": "Isometric (svg-iso)",
}

THUMB_WIDTH = 480
THUMB_HEIGHT = 360
PADDING = 16
SECTION_HEADER_HEIGHT = 48
COL_HEADER_HEIGHT = 32
ROW_LABEL_WIDTH = 140


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("Arial.ttf", "Helvetica.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _svg_filename(fmt: str, theme: str, icon_set: str) -> str:
    return f"{fmt}_{theme}_{icon_set}.svg"


def _normalize_client_vlans() -> None:
    """Set all client VLANs to 1 for uniform link colors in theme showcase."""
    data = json.loads(MOCK_DATA.read_text())
    for client in data.get("clients", []):
        client["vlan"] = 1
    # Also simplify vlan_info
    data["vlan_info"] = [{"id": 1, "name": "LAN", "client_count": len(data.get("clients", []))}]
    MOCK_DATA.write_text(json.dumps(data, indent=2, sort_keys=True))


def generate_mock_data() -> None:
    """Generate mock data with a complex network topology."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    python = sys.executable
    cmd = [
        python,
        "-m",
        "unifi_network_maps.cli",
        "--generate-mock",
        str(MOCK_DATA),
        "--mock-seed",
        str(MOCK_SEED),
        "--mock-switches",
        str(MOCK_SWITCHES),
        "--mock-aps",
        str(MOCK_APS),
        "--mock-wired-clients",
        str(MOCK_WIRED_CLIENTS),
        "--mock-wireless-clients",
        str(MOCK_WIRELESS_CLIENTS),
    ]
    subprocess.run(
        cmd,
        check=True,
        env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
    )
    # Normalize all client VLANs to 1 for cleaner theme showcase
    _normalize_client_vlans()


def generate_svgs() -> list[Path]:
    """Run the CLI to produce all 40 SVGs, return list of paths."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    paths: list[Path] = []

    for fmt in FORMATS:
        for theme in THEMES:
            for icon_set in ICON_SETS:
                out = OUTPUT_DIR / _svg_filename(fmt, theme, icon_set)
                cmd = [
                    python,
                    "-m",
                    "unifi_network_maps.cli",
                    "--mock-data",
                    str(MOCK_DATA),
                    "--include-clients",
                    "--client-scope",
                    "all",
                    "--theme",
                    theme,
                    "--icon-set",
                    icon_set,
                    "--format",
                    fmt,
                    "--output",
                    str(out),
                ]
                print(f"  {out.name}")
                subprocess.run(
                    cmd,
                    check=True,
                    env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")},
                )
                paths.append(out)

    return paths


def _svg_to_thumb(svg_path: Path, width: int, height: int) -> Image.Image:
    """Convert an SVG to a PIL Image thumbnail at the given size."""
    png_bytes = cairosvg.svg2png(url=str(svg_path), output_width=width * 2)
    img = Image.open(__import__("io").BytesIO(png_bytes))
    img.thumbnail((width, height), Image.Resampling.LANCZOS)
    return img


def assemble_composite() -> Path:
    """Build the composite PNG from the individual SVGs."""
    font_section = _load_font(24)
    font_col = _load_font(16)
    font_row = _load_font(14)

    cols = len(ICON_SETS)
    rows = len(THEMES)

    grid_width = ROW_LABEL_WIDTH + cols * (THUMB_WIDTH + PADDING) + PADDING
    section_height = SECTION_HEADER_HEIGHT + COL_HEADER_HEIGHT + rows * (THUMB_HEIGHT + PADDING)
    total_height = len(FORMATS) * section_height + PADDING
    total_width = grid_width

    canvas = Image.new("RGB", (total_width, total_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    y_offset = 0

    for fmt in FORMATS:
        # Section header
        header = FORMAT_LABELS[fmt]
        bbox = draw.textbbox((0, 0), header, font=font_section)
        text_w = bbox[2] - bbox[0]
        draw.text(
            ((total_width - text_w) / 2, y_offset + 10),
            header,
            fill=(30, 30, 30),
            font=font_section,
        )
        y_offset += SECTION_HEADER_HEIGHT

        # Column headers
        for ci, icon_set in enumerate(ICON_SETS):
            label = icon_set.capitalize()
            bbox = draw.textbbox((0, 0), label, font=font_col)
            text_w = bbox[2] - bbox[0]
            x = ROW_LABEL_WIDTH + ci * (THUMB_WIDTH + PADDING) + (THUMB_WIDTH - text_w) / 2
            draw.text((x, y_offset + 6), label, fill=(60, 60, 60), font=font_col)
        y_offset += COL_HEADER_HEIGHT

        # Rows
        for theme in THEMES:
            # Row label
            label = THEME_LABELS[theme]
            bbox = draw.textbbox((0, 0), label, font=font_row)
            text_h = bbox[3] - bbox[1]
            draw.text(
                (PADDING, y_offset + (THUMB_HEIGHT - text_h) / 2),
                label,
                fill=(60, 60, 60),
                font=font_row,
            )

            for ci, icon_set in enumerate(ICON_SETS):
                svg_path = OUTPUT_DIR / _svg_filename(fmt, theme, icon_set)
                if svg_path.exists():
                    thumb = _svg_to_thumb(svg_path, THUMB_WIDTH, THUMB_HEIGHT)
                    x = ROW_LABEL_WIDTH + ci * (THUMB_WIDTH + PADDING)
                    # Centre the thumbnail vertically in the cell
                    y = y_offset + (THUMB_HEIGHT - thumb.height) // 2
                    canvas.paste(thumb, (x, y))

            y_offset += THUMB_HEIGHT + PADDING

    out = OUTPUT_DIR / "theme_matrix.png"
    canvas.save(out, "PNG")
    return out


def main() -> None:
    print("Generating mock data with complex topology ...")
    generate_mock_data()

    print(f"Generating {len(THEMES) * len(ICON_SETS) * len(FORMATS)} SVGs ...")
    generate_svgs()

    print("Assembling composite PNG ...")
    out = assemble_composite()
    print(f"Done: {out}")


if __name__ == "__main__":
    main()
