# Render helpers

This package contains rendering utilities used by CLI formats:

- `legend.py` centralizes legend selection and rendering for Mermaid outputs.
- `markdown_tables.py` provides shared helpers for consistent Markdown table output.
- `mkdocs.py` focuses on MkDocs-specific layout (dual theme, sidebar legend).
- `templating.py` and `templates/` provide Jinja2-based Markdown/HTML/CSS/JS templates.

Keep render logic here and avoid pushing format-specific utilities back into the CLI.
