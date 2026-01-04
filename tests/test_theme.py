from unifi_network_maps.render.theme import load_theme


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
