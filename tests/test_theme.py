import pytest

from unifi_network_maps.render.theme import BUILTIN_THEMES, load_theme, resolve_themes


def test_load_theme_rejects_non_object(tmp_path):
    path = tmp_path / "theme.yaml"
    path.write_text("- nope\n", encoding="utf-8")

    try:
        load_theme(path)
    except ValueError as exc:
        message = str(exc)
    else:
        message = ""

    assert "Theme file must contain a YAML mapping" in message


def test_load_theme_applies_mermaid_gateway_colors(tmp_path):
    path = tmp_path / "theme.yaml"
    path.write_text(
        'mermaid:\n  nodes:\n    gateway:\n      fill: "#111111"\n      stroke: "#222222"\n',
        encoding="utf-8",
    )

    mermaid_theme, _svg_theme = load_theme(path)

    assert mermaid_theme.node_gateway == ("#111111", "#222222")


def test_load_theme_applies_svg_link_colors(tmp_path):
    path = tmp_path / "theme.yaml"
    path.write_text(
        'svg:\n  links:\n    standard:\n      from: "#abc"\n      to: "#def"\n',
        encoding="utf-8",
    )

    _mermaid_theme, svg_theme = load_theme(path)

    assert svg_theme.link_standard == ("#abc", "#def")


def test_load_theme_applies_new_svg_properties(tmp_path):
    """Test that new theme properties (background, text, status, wan_globe) are loaded."""
    path = tmp_path / "theme.yaml"
    path.write_text(
        """svg:
  background: "#111"
  text:
    primary: "#222"
    secondary: "#333"
  status:
    online: "#444"
    offline: "#555"
  wan_globe:
    from: "#666"
    to: "#777"
""",
        encoding="utf-8",
    )

    _mermaid_theme, svg_theme = load_theme(path)

    assert svg_theme.background == "#111"
    assert svg_theme.text_primary == "#222"
    assert svg_theme.text_secondary == "#333"
    assert svg_theme.status_online == "#444"
    assert svg_theme.status_offline == "#555"
    assert svg_theme.wan_globe == ("#666", "#777")


def test_resolve_themes_builtin_unifi():
    """Test that built-in unifi theme loads correctly."""
    mermaid_theme, svg_theme = resolve_themes(theme_name="unifi")

    assert svg_theme.background == "#f9fafa"
    assert "#006fff" in mermaid_theme.node_gateway  # UniFi blue


def test_resolve_themes_builtin_unifi_dark():
    """Test that built-in unifi-dark theme loads correctly."""
    _mermaid_theme, svg_theme = resolve_themes(theme_name="unifi-dark")

    assert svg_theme.background == "#1c1e21"
    assert svg_theme.text_primary == "#f9fafa"


def test_resolve_themes_builtin_minimal():
    """Test that built-in minimal theme loads correctly."""
    _mermaid_theme, svg_theme = resolve_themes(theme_name="minimal")

    assert svg_theme.background == "#fafafa"


def test_resolve_themes_builtin_classic():
    """Test that classic theme maps to default.yaml."""
    mermaid_theme, svg_theme = resolve_themes(theme_name="classic")

    # Should use default theme values
    assert svg_theme.link_standard is not None
    assert mermaid_theme.node_gateway is not None


def test_resolve_themes_file_takes_priority(tmp_path):
    """Test that --theme-file takes priority over --theme."""
    path = tmp_path / "custom.yaml"
    path.write_text(
        'svg:\n  background: "#custom"\n',
        encoding="utf-8",
    )

    _mermaid_theme, svg_theme = resolve_themes(
        theme_name="unifi",  # This should be ignored
        theme_file=path,
    )

    assert svg_theme.background == "#custom"


def test_resolve_themes_invalid_name_raises():
    """Test that invalid theme name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown theme"):
        resolve_themes(theme_name="invalid-theme")


def test_builtin_themes_all_exist():
    """Test that all built-in themes can be loaded."""
    for theme_name in BUILTIN_THEMES:
        mermaid_theme, svg_theme = resolve_themes(theme_name=theme_name)
        assert mermaid_theme is not None
        assert svg_theme is not None
