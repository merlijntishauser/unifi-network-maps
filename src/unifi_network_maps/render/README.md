# Render helpers

This package contains CLI-specific rendering utilities:

- `__init__.py` re-exports rendering functions from `unifi_topology.render`.
- `legend.py` centralizes legend selection and rendering for Mermaid outputs.
- `mkdocs.py` focuses on MkDocs-specific layout (dual theme, sidebar legend, section templates).
- `theme.py` loads and resolves Mermaid and SVG themes, delegating to the library.
- `templating.py` and `templates/` provide Jinja2-based Markdown/HTML/CSS/JS templates.

Mermaid, LLDP, device port, and inventory rendering live in `unifi-topology`.
Keep CLI-specific format logic here and avoid pushing it back into the library.
