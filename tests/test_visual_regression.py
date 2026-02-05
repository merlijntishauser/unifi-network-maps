"""Visual regression tests for SVG output.

Compares rendered SVG files against baseline PNG images.
Uses cairosvg for rendering and Pillow for pixel comparison.

To update baselines after intentional changes:
    pytest tests/test_visual_regression.py --update-baselines

To run visual regression tests:
    pytest tests/test_visual_regression.py -v
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

pytestmark = pytest.mark.acceptance

if TYPE_CHECKING:
    from collections.abc import Generator

# Skip all tests if cairosvg/Pillow not installed
cairosvg = pytest.importorskip("cairosvg")
Image: Any = pytest.importorskip("PIL.Image")

SMOKETEST_DIR = Path(__file__).parent.parent / "smoketest-mock"
BASELINE_DIR = Path(__file__).parent / "baselines"

# SVG files to test (relative to smoketest-mock/)
SVG_FILES = [
    "network_grouped.svg",
    "network_grouped_iso.svg",
    "network_ports_clients_iso.svg",
]

# Threshold for pixel difference (0-255 per channel)
PIXEL_THRESHOLD = 10
# Percentage of pixels allowed to differ (1% allows for minor cross-platform font rendering differences)
DIFF_PERCENT_THRESHOLD = 1.0


@pytest.fixture(scope="session")
def update_baselines(request: pytest.FixtureRequest) -> bool:
    """Check if we should update baselines."""
    return bool(request.config.getoption("--update-baselines", default=False))


@pytest.fixture(scope="session", autouse=True)
def ensure_baseline_dir() -> Generator[None]:
    """Ensure baseline directory exists."""
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    yield


def svg_to_png(svg_path: Path, scale: float = 2.0) -> Any:
    """Render SVG to PNG image at given scale."""
    svg_content = svg_path.read_bytes()
    png_data = cairosvg.svg2png(bytestring=svg_content, scale=scale)
    return Image.open(BytesIO(png_data)).convert("RGBA")


def compute_diff_percentage(img1: Any, img2: Any) -> tuple[float, Any]:
    """Compute percentage of differing pixels and generate diff image."""
    # Ensure same size
    if img1.size != img2.size:
        # Resize to larger dimensions for comparison
        max_w = max(img1.width, img2.width)
        max_h = max(img1.height, img2.height)
        img1 = img1.resize((max_w, max_h), Image.Resampling.NEAREST)
        img2 = img2.resize((max_w, max_h), Image.Resampling.NEAREST)

    pixels1 = img1.load()
    pixels2 = img2.load()
    width, height = img1.size

    diff_img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    diff_pixels = diff_img.load()

    diff_count = 0
    total_pixels = width * height

    for y in range(height):
        for x in range(width):
            p1 = pixels1[x, y]
            p2 = pixels2[x, y]

            # Calculate per-channel difference
            channel_diff = max(abs(p1[i] - p2[i]) for i in range(4))

            if channel_diff > PIXEL_THRESHOLD:
                diff_count += 1
                # Highlight differences in red
                diff_pixels[x, y] = (255, 0, 0, 255)
            else:
                # Show original pixel (faded)
                diff_pixels[x, y] = (p1[0], p1[1], p1[2], 128)

    diff_percentage = (diff_count / total_pixels) * 100 if total_pixels > 0 else 0
    return diff_percentage, diff_img


def save_comparison(
    baseline: Any | None,
    current: Any,
    diff: Any | None,
    output_path: Path,
) -> None:
    """Save side-by-side comparison image."""
    images = [img for img in [baseline, current, diff] if img is not None]
    if not images:
        return

    # Calculate combined dimensions
    max_height = max(img.height for img in images)
    total_width = sum(img.width for img in images) + (len(images) - 1) * 10

    combined = Image.new("RGBA", (total_width, max_height), (240, 240, 240, 255))

    x_offset = 0
    for img in images:
        combined.paste(img, (x_offset, 0))
        x_offset += img.width + 10

    combined.save(output_path)


class TestVisualRegression:
    """Visual regression tests for smoketest SVG output."""

    @pytest.mark.parametrize("svg_file", SVG_FILES)
    def test_svg_visual_regression(
        self,
        svg_file: str,
        update_baselines: bool,
        tmp_path: Path,
    ) -> None:
        """Compare rendered SVG against baseline image."""
        svg_path = SMOKETEST_DIR / svg_file
        baseline_name = svg_file.replace(".svg", ".png")
        baseline_path = BASELINE_DIR / baseline_name

        if not svg_path.exists():
            pytest.skip(f"SVG file not found: {svg_path}")

        # Render current SVG
        current_img = svg_to_png(svg_path)

        if update_baselines:
            # Update mode: save current as baseline
            current_img.save(baseline_path)
            pytest.skip(f"Updated baseline: {baseline_path}")

        if not baseline_path.exists():
            # No baseline exists - create it
            current_img.save(baseline_path)
            pytest.fail(
                f"No baseline existed. Created new baseline at {baseline_path}. "
                "Review and commit if correct."
            )

        # Load baseline and compare
        baseline_img = Image.open(baseline_path).convert("RGBA")
        diff_pct, diff_img = compute_diff_percentage(baseline_img, current_img)

        if diff_pct > DIFF_PERCENT_THRESHOLD:
            # Save comparison for debugging
            comparison_path = tmp_path / f"comparison_{svg_file.replace('.svg', '.png')}"
            save_comparison(baseline_img, current_img, diff_img, comparison_path)

            pytest.fail(
                f"Visual regression failed for {svg_file}:\n"
                f"  {diff_pct:.2f}% pixels differ (threshold: {DIFF_PERCENT_THRESHOLD}%)\n"
                f"  Comparison saved to: {comparison_path}\n"
                f"  Run with --update-baselines to accept changes."
            )

    def test_baseline_dimensions_reasonable(self) -> None:
        """Verify baseline images have reasonable dimensions."""
        for baseline in BASELINE_DIR.glob("*.png"):
            img = Image.open(baseline)
            # SVGs at 2x scale should be reasonably sized
            assert img.width > 100, f"{baseline.name} too narrow: {img.width}px"
            assert img.height > 100, f"{baseline.name} too short: {img.height}px"
            assert img.width < 10000, f"{baseline.name} too wide: {img.width}px"
            assert img.height < 10000, f"{baseline.name} too tall: {img.height}px"
