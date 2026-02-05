"""Automated validation of smoketest outputs.

These tests verify the structural integrity of generated outputs
without requiring visual inspection.

Run `make smoketest-mock` to generate the required files before running these tests.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SMOKETEST_DIR = Path(__file__).parent.parent / "smoketest-mock"

# Skip all tests in this module if smoketest-mock directory doesn't exist
pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.skipif(
        not SMOKETEST_DIR.exists(),
        reason="smoketest-mock directory not found. Run 'make smoketest-mock' first.",
    ),
]


# --- SVG Validation ---


class TestSvgStructure:
    """Validate SVG file structure and required elements."""

    @pytest.fixture
    def grouped_iso_svg(self) -> str:
        return (SMOKETEST_DIR / "network_grouped_iso.svg").read_text()

    @pytest.fixture
    def grouped_svg(self) -> str:
        return (SMOKETEST_DIR / "network_grouped.svg").read_text()

    @pytest.fixture
    def ports_clients_iso_svg(self) -> str:
        return (SMOKETEST_DIR / "network_ports_clients_iso.svg").read_text()

    def test_grouped_iso_has_valid_svg_root(self, grouped_iso_svg: str) -> None:
        """SVG has valid root element with viewBox."""
        assert grouped_iso_svg.startswith("<svg")
        assert 'xmlns="http://www.w3.org/2000/svg"' in grouped_iso_svg
        assert "viewBox=" in grouped_iso_svg

    def test_grouped_iso_has_defs(self, grouped_iso_svg: str) -> None:
        """SVG contains gradient definitions."""
        assert "<defs>" in grouped_iso_svg
        assert "linearGradient" in grouped_iso_svg

    def test_grouped_iso_has_style(self, grouped_iso_svg: str) -> None:
        """SVG contains style element."""
        assert "<style>" in grouped_iso_svg
        assert "font-family" in grouped_iso_svg

    def test_grouped_iso_has_network_groups(self, grouped_iso_svg: str) -> None:
        """SVG contains network group elements."""
        assert 'class="network-group"' in grouped_iso_svg
        # Check for expected groups
        assert 'data-group-name="gateway"' in grouped_iso_svg
        assert 'data-group-name="switch"' in grouped_iso_svg
        assert 'data-group-name="ap"' in grouped_iso_svg

    def test_grouped_iso_has_group_boundaries(self, grouped_iso_svg: str) -> None:
        """SVG contains group boundary polygons."""
        assert 'class="group-boundary"' in grouped_iso_svg
        # Isometric uses polygons
        assert "<polygon" in grouped_iso_svg

    def test_grouped_iso_has_group_labels(self, grouped_iso_svg: str) -> None:
        """SVG contains group labels with proper styling."""
        assert 'class="group-label"' in grouped_iso_svg
        # Labels should have reasonable font size
        label_sizes = re.findall(r'class="group-label"[^>]*font-size="(\d+)"', grouped_iso_svg)
        assert len(label_sizes) > 0
        for size in label_sizes:
            assert 24 <= int(size) <= 200, f"Label size {size} out of expected range"

    def test_grouped_iso_has_nodes(self, grouped_iso_svg: str) -> None:
        """SVG contains node elements."""
        assert 'class="unm-node"' in grouped_iso_svg
        node_count = grouped_iso_svg.count('class="unm-node"')
        assert node_count >= 3, f"Expected at least 3 nodes, got {node_count}"

    def test_grouped_iso_has_grid(self, grouped_iso_svg: str) -> None:
        """Isometric SVG contains grid lines."""
        assert 'class="iso-grid"' in grouped_iso_svg

    def test_grouped_iso_viewport_positive(self, grouped_iso_svg: str) -> None:
        """ViewBox starts at 0,0 (no negative clipping)."""
        match = re.search(r'viewBox="([^"]+)"', grouped_iso_svg)
        assert match
        viewbox = match.group(1).split()
        assert float(viewbox[0]) == 0
        assert float(viewbox[1]) == 0
        assert float(viewbox[2]) > 0
        assert float(viewbox[3]) > 0

    def test_grouped_svg_has_rect_boundaries(self, grouped_svg: str) -> None:
        """Non-isometric SVG uses rect for group boundaries."""
        assert 'class="group-boundary"' in grouped_svg
        assert "<rect" in grouped_svg

    def test_ports_clients_has_nodes(self, ports_clients_iso_svg: str) -> None:
        """Ports+clients SVG has multiple nodes."""
        node_count = ports_clients_iso_svg.count('class="unm-node"')
        assert node_count >= 3


class TestSvgGeometry:
    """Validate SVG geometric properties."""

    @pytest.fixture
    def svg_content(self) -> str:
        return (SMOKETEST_DIR / "network_grouped_iso.svg").read_text()

    @pytest.fixture
    def svg_root(self) -> ET.Element:
        svg_path = SMOKETEST_DIR / "network_grouped_iso.svg"
        # Parse with namespace handling
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        tree = ET.parse(svg_path)
        return tree.getroot()

    @pytest.fixture
    def viewbox_dims(self, svg_root: ET.Element) -> tuple[float, float, float, float]:
        """Extract viewBox dimensions."""
        viewbox = svg_root.get("viewBox", "0 0 0 0").split()
        return tuple(float(v) for v in viewbox)  # type: ignore[return-value]

    def test_viewbox_dimensions_reasonable(self, svg_root: ET.Element) -> None:
        """ViewBox has reasonable dimensions."""
        viewbox = svg_root.get("viewBox", "").split()
        assert len(viewbox) == 4
        width = float(viewbox[2])
        height = float(viewbox[3])
        # Should be larger than minimum useful size
        assert width >= 500, f"ViewBox width {width} too small"
        assert height >= 400, f"ViewBox height {height} too small"
        # Should not be absurdly large
        assert width <= 10000, f"ViewBox width {width} too large"
        assert height <= 10000, f"ViewBox height {height} too large"

    def test_node_positions_inside_viewport(
        self, svg_content: str, viewbox_dims: tuple[float, float, float, float]
    ) -> None:
        """All node center positions are within viewport bounds."""
        _, _, vb_width, vb_height = viewbox_dims
        # Extract node polygon points (isometric nodes use polygons)
        # Pattern: <polygon points="x1,y1 x2,y2 ..." in node groups
        node_pattern = r'class="unm-node"[^>]*>.*?<polygon[^>]*points="([^"]+)"'
        nodes = re.findall(node_pattern, svg_content, re.DOTALL)

        assert len(nodes) > 0, "No nodes found"

        for points_str in nodes:
            points = [tuple(map(float, p.split(","))) for p in points_str.split()]
            # Calculate center of polygon
            center_x = sum(p[0] for p in points) / len(points)
            center_y = sum(p[1] for p in points) / len(points)

            # Allow small margin outside viewport (for partial visibility)
            margin = 50
            assert -margin <= center_x <= vb_width + margin, (
                f"Node center x={center_x} outside viewport"
            )
            assert -margin <= center_y <= vb_height + margin, (
                f"Node center y={center_y} outside viewport"
            )

    def test_group_boundaries_inside_viewport(
        self, svg_content: str, viewbox_dims: tuple[float, float, float, float]
    ) -> None:
        """Group boundary polygons are mostly within viewport."""
        _, _, vb_width, vb_height = viewbox_dims
        # Extract group boundary polygon points
        boundary_pattern = r'class="group-boundary"[^>]*points="([^"]+)"'
        boundaries = re.findall(boundary_pattern, svg_content)

        assert len(boundaries) > 0, "No group boundaries found"

        for points_str in boundaries:
            points = [tuple(map(float, p.split(","))) for p in points_str.split()]
            # At least one corner should be inside viewport
            inside_count = sum(1 for x, y in points if 0 <= x <= vb_width and 0 <= y <= vb_height)
            assert inside_count >= 1, (
                f"Group boundary completely outside viewport: {points_str[:50]}..."
            )

    def test_no_extremely_negative_node_coordinates(self, svg_content: str) -> None:
        """Node and group elements don't have extremely negative coordinates."""
        # Check node polygon coordinates (not grid lines which extend far)
        node_pattern = r'class="unm-node"[^>]*>.*?<polygon[^>]*points="([^"]+)"'
        nodes = re.findall(node_pattern, svg_content, re.DOTALL)

        for points_str in nodes:
            points = [tuple(map(float, p.split(","))) for p in points_str.split()]
            for x, y in points:
                assert x >= -500, f"Node has extremely negative x: {x}"
                assert y >= -500, f"Node has extremely negative y: {y}"

        # Check group boundary coordinates
        boundary_pattern = r'class="group-boundary"[^>]*points="([^"]+)"'
        boundaries = re.findall(boundary_pattern, svg_content)

        for points_str in boundaries:
            points = [tuple(map(float, p.split(","))) for p in points_str.split()]
            for x, y in points:
                assert x >= -500, f"Group boundary has extremely negative x: {x}"
                assert y >= -500, f"Group boundary has extremely negative y: {y}"

    def test_group_labels_have_valid_positions(
        self, svg_content: str, viewbox_dims: tuple[float, float, float, float]
    ) -> None:
        """Group labels are positioned within reasonable bounds."""
        _, _, vb_width, vb_height = viewbox_dims
        # Extract label positions
        label_pattern = r'class="group-label"[^>]*x="([^"]+)"[^>]*y="([^"]+)"'
        labels = re.findall(label_pattern, svg_content)

        assert len(labels) > 0, "No group labels found"

        for x_str, y_str in labels:
            x, y = float(x_str), float(y_str)
            # Labels should be inside viewport (with margin for transformed text)
            margin = 200  # Larger margin due to transforms
            assert -margin <= x <= vb_width + margin, f"Label x={x} far outside viewport"
            assert -margin <= y <= vb_height + margin, f"Label y={y} far outside viewport"

    def test_edges_connect_valid_points(self, svg_content: str) -> None:
        """Edge paths have valid coordinates."""
        # Extract path d attributes for edges
        path_pattern = r'<path[^>]*d="M\s*(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+L'
        paths = re.findall(path_pattern, svg_content)

        for x_str, y_str in paths:
            x, y = float(x_str), float(y_str)
            # Path start points should not be extremely negative
            assert x >= -1000, f"Edge path starts at extreme x={x}"
            assert y >= -1000, f"Edge path starts at extreme y={y}"


# --- Mermaid Validation ---


class TestMermaidStructure:
    """Validate Mermaid diagram file structure."""

    @pytest.fixture
    def mermaid_content(self) -> str:
        return (SMOKETEST_DIR / "network_ports.mmd").read_text()

    def test_has_graph_declaration(self, mermaid_content: str) -> None:
        """Mermaid file starts with graph declaration."""
        assert mermaid_content.strip().startswith("graph ")

    def test_has_node_definitions(self, mermaid_content: str) -> None:
        """Mermaid contains node definitions with labels."""
        # Pattern: node_id["Label"]
        assert re.search(r'\w+\["[^"]+"\]', mermaid_content)

    def test_has_edges(self, mermaid_content: str) -> None:
        """Mermaid contains edge connections."""
        # Pattern: node1 ---|"label"| node2 or node1 --> node2
        # Note: --> is Mermaid arrow syntax, not HTML comment
        assert re.search(r'---\|"|-->|---\s+\w', mermaid_content)  # CodeQL: not HTML

    def test_has_class_definitions(self, mermaid_content: str) -> None:
        """Mermaid contains node class assignments."""
        assert "class " in mermaid_content
        assert "node_gateway" in mermaid_content
        assert "node_switch" in mermaid_content
        assert "node_ap" in mermaid_content

    def test_has_classdefs(self, mermaid_content: str) -> None:
        """Mermaid contains classDef styling."""
        assert "classDef node_gateway" in mermaid_content
        assert "classDef node_switch" in mermaid_content
        assert "classDef node_ap" in mermaid_content

    def test_classdefs_have_colors(self, mermaid_content: str) -> None:
        """ClassDef definitions include fill and stroke colors."""
        classdef_pattern = r"classDef\s+\w+\s+fill:#[0-9a-fA-F]+,stroke:#[0-9a-fA-F]+"
        matches = re.findall(classdef_pattern, mermaid_content)
        assert len(matches) >= 3, "Expected at least 3 styled classDefs"

    def test_has_linkstyle(self, mermaid_content: str) -> None:
        """Mermaid contains linkStyle for edge styling."""
        assert "linkStyle" in mermaid_content

    def test_no_syntax_errors(self, mermaid_content: str) -> None:
        """Basic syntax validation - balanced brackets."""
        assert mermaid_content.count("[") == mermaid_content.count("]")
        assert mermaid_content.count("{") == mermaid_content.count("}")
        assert mermaid_content.count("(") == mermaid_content.count(")")


# --- MkDocs Validation ---


class TestMkdocsStructure:
    """Validate MkDocs markdown file structure."""

    @pytest.fixture
    def mkdocs_content(self) -> str:
        return (SMOKETEST_DIR / "unifi-network-dual-theme-and-clients.md").read_text()

    def test_has_title(self, mkdocs_content: str) -> None:
        """Markdown has H1 title."""
        assert mkdocs_content.startswith("# ")

    def test_has_timestamp(self, mkdocs_content: str) -> None:
        """Markdown contains generation timestamp."""
        assert "Generated:" in mkdocs_content
        # Check for date pattern
        assert re.search(r"\d{4}-\d{2}-\d{2}", mkdocs_content)

    def test_has_mermaid_blocks(self, mkdocs_content: str) -> None:
        """Markdown contains mermaid code blocks."""
        assert "```mermaid" in mkdocs_content
        # Should have opening and closing
        mermaid_opens = mkdocs_content.count("```mermaid")
        code_closes = mkdocs_content.count("```")
        assert mermaid_opens >= 1
        assert code_closes >= mermaid_opens * 2  # Each block has open + close

    def test_has_dual_theme_support(self, mkdocs_content: str) -> None:
        """Markdown has light/dark theme CSS."""
        assert "unifi-mermaid--light" in mkdocs_content
        assert "unifi-mermaid--dark" in mkdocs_content
        assert "[data-md-color-scheme=" in mkdocs_content

    def test_has_legend(self, mkdocs_content: str) -> None:
        """Markdown contains legend section."""
        assert "unifi-legend" in mkdocs_content
        # Check for legend items
        assert "Gateway" in mkdocs_content
        assert "Switch" in mkdocs_content
        assert "AP" in mkdocs_content

    def test_has_style_block(self, mkdocs_content: str) -> None:
        """Markdown contains style block for theming."""
        assert "<style>" in mkdocs_content
        assert "</style>" in mkdocs_content

    def test_mermaid_graph_valid(self, mkdocs_content: str) -> None:
        """Embedded mermaid graphs have valid structure."""
        # Extract mermaid blocks
        mermaid_blocks = re.findall(r"```mermaid\n(.*?)```", mkdocs_content, re.DOTALL)
        assert len(mermaid_blocks) >= 1

        for block in mermaid_blocks:
            # Should have graph declaration
            assert "graph " in block or "%%{init:" in block
            # Should have nodes
            assert re.search(r'\w+\["[^"]+"\]', block)

    def test_legend_has_colors(self, mkdocs_content: str) -> None:
        """Legend contains color swatches."""
        # Pattern for inline color swatches
        assert re.search(r"background:#[0-9a-fA-F]+", mkdocs_content)
        assert re.search(r"border:.*#[0-9a-fA-F]+", mkdocs_content)


# --- Cross-format Consistency ---


class TestCrossFormatConsistency:
    """Validate consistency across different output formats."""

    @pytest.fixture
    def all_contents(self) -> dict[str, str]:
        return {
            "svg_iso": (SMOKETEST_DIR / "network_grouped_iso.svg").read_text(),
            "svg": (SMOKETEST_DIR / "network_grouped.svg").read_text(),
            "mermaid": (SMOKETEST_DIR / "network_ports.mmd").read_text(),
            "mkdocs": (SMOKETEST_DIR / "unifi-network-dual-theme-and-clients.md").read_text(),
        }

    def test_same_device_names_across_formats(self, all_contents: dict[str, str]) -> None:
        """Core device names appear in all formats."""
        # These should be in the mock data
        expected_devices = ["Cloud Gateway", "Core Switch"]

        for device in expected_devices:
            # SVG uses data attributes or text content
            assert device in all_contents["svg_iso"], f"{device} not in SVG iso"
            assert device in all_contents["svg"], f"{device} not in SVG"
            # Mermaid uses labels in brackets
            assert device in all_contents["mermaid"], f"{device} not in Mermaid"
            # MkDocs embeds mermaid
            assert device in all_contents["mkdocs"], f"{device} not in MkDocs"

    def test_node_type_styling_present(self, all_contents: dict[str, str]) -> None:
        """All formats include node type styling."""
        for fmt, content in all_contents.items():
            # Each format should reference gateway/switch/ap types
            has_gateway = "gateway" in content.lower()
            has_switch = "switch" in content.lower()
            has_ap = "ap" in content.lower() or "node_ap" in content
            assert has_gateway, f"Gateway type missing in {fmt}"
            assert has_switch, f"Switch type missing in {fmt}"
            assert has_ap, f"AP type missing in {fmt}"
