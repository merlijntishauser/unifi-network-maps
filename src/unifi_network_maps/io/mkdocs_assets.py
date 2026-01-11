"""MkDocs asset output helpers."""

from __future__ import annotations

from pathlib import Path


def write_mkdocs_sidebar_assets(output_path: str) -> None:
    output_dir = Path(output_path).resolve().parent
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "legend.js").write_text(
        (
            'document.addEventListener("DOMContentLoaded", () => {\n'
            '  const legends = document.querySelectorAll("[data-unifi-legend]");\n'
            '  const sidebar = document.querySelector(".md-sidebar--secondary .md-sidebar__scrollwrap");\n'
            "  if (!legends.length || !sidebar) {\n"
            "    return;\n"
            "  }\n"
            '  const wrapper = document.createElement("div");\n'
            '  wrapper.className = "unifi-legend-sidebar";\n'
            '  const title = document.createElement("div");\n'
            '  title.className = "unifi-legend-title";\n'
            '  title.textContent = "Legend";\n'
            "  wrapper.appendChild(title);\n"
            "  legends.forEach((legend) => {\n"
            "    wrapper.appendChild(legend.cloneNode(true));\n"
            '    legend.classList.add("unifi-legend-hidden");\n'
            "  });\n"
            "  sidebar.appendChild(wrapper);\n"
            "});\n"
        ),
        encoding="utf-8",
    )
    (assets_dir / "legend.css").write_text(
        (
            ".unifi-legend-hidden,\n"
            ".unifi-legend-hidden.unifi-legend,\n"
            ".unifi-legend-hidden.unifi-legend--light,\n"
            ".unifi-legend-hidden.unifi-legend--dark {\n"
            "  display: none !important;\n"
            "}\n\n"
            ".unifi-legend-sidebar {\n"
            "  margin-top: 1rem;\n"
            "  padding: 0.5rem 0.75rem;\n"
            "  border: 1px solid rgba(0, 0, 0, 0.08);\n"
            "  border-radius: 6px;\n"
            "  font-size: 0.75rem;\n"
            "}\n\n"
            ".unifi-legend-title {\n"
            "  font-weight: 600;\n"
            "  margin-bottom: 0.5rem;\n"
            "}\n\n"
            ".unifi-legend-sidebar table {\n"
            "  width: 100%;\n"
            "  border-collapse: collapse;\n"
            "}\n\n"
            ".unifi-legend-sidebar td,\n"
            ".unifi-legend-sidebar th {\n"
            "  border: 0;\n"
            "  padding: 0.15rem 0;\n"
            "}\n\n"
            ".unifi-legend-sidebar svg {\n"
            "  display: block;\n"
            "}\n"
        ),
        encoding="utf-8",
    )
