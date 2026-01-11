"""Jinja2 helpers for Markdown/HTML rendering."""

from __future__ import annotations

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

_ENV = Environment(
    loader=PackageLoader("unifi_network_maps.render", "templates"),
    autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)


def render_template(name: str, **context: object) -> str:
    template = _ENV.get_template(name)
    return template.render(**context)
