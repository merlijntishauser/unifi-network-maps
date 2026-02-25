# CLAUDE.md

Quick reference for AI assistants working on this codebase.

## Project Overview

**unifi-network-maps** - A Python CLI tool that generates network diagrams (Mermaid, SVG, MkDocs) from UniFi Network Controller data via LLDP topology.

- **Version**: 1.6.4
- **Python**: 3.12+ (3.13 preferred)
- **License**: MIT
- **PyPI**: `pip install unifi-network-maps`

## Architecture

```
unifi-topology (library) → unifi-network-maps (CLI)
  Model + Adapters + SVG     Mermaid + MkDocs + CLI + IO
```

The model layer, adapters, SVG renderer, and assets live in the `unifi-topology` library.
This CLI depends on `unifi-topology` and adds Mermaid rendering, MkDocs output, CLI argument
parsing, and file I/O.

### Source Layout

```
src/unifi_network_maps/
├── cli/                 # CLI entry point, argument parsing
│   ├── args.py          # Argument definitions
│   ├── main.py          # Main entry point
│   ├── render.py        # Render dispatch
│   └── runtime.py       # Runtime context
├── render/              # CLI-only renderers (Mermaid, MkDocs, markdown)
│   ├── __init__.py      # Re-exports from unifi_topology.render
│   ├── mermaid.py       # Mermaid output
│   ├── mermaid_theme.py # Mermaid theming
│   ├── theme.py         # Mermaid theme loading + library SVG delegation
│   ├── legend.py        # Legend rendering
│   ├── mkdocs.py        # MkDocs format
│   ├── lldp_md.py       # LLDP markdown tables
│   ├── device_summary.py    # Device summary sections
│   ├── device_ports_md.py   # Device port markdown
│   ├── device_ports_aggregate.py # Aggregated port tables
│   ├── markdown_tables.py   # Generic markdown table helpers
│   ├── templating.py    # Jinja2 templates
│   └── templates/       # Jinja2 template files
├── io/
│   ├── export.py        # File export
│   ├── mock_data.py     # Mock data loading
│   ├── mock_generate.py # Mock generation entry point
│   ├── mkdocs_assets.py # MkDocs sidebar asset writing
│   ├── paths.py         # Path resolution utilities
│   └── debug.py         # Debug dump utilities
```

### Library dependency

Model, adapters, SVG rendering, and assets are provided by `unifi-topology`:
- `unifi_topology.model.*` -- topology, devices, edges, clients, VLANs, etc.
- `unifi_topology.adapters.*` -- UniFi API, config, DNS
- `unifi_topology.render.*` -- SVG, SVG isometric, inventory table, SVG theming

## Development Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
pip install -r requirements-dev.txt -c constraints.txt
pre-commit install

# Editable install
pip install -e .

# Linting and type checking
ruff check .
ruff format .
pyright

# Testing
pytest                    # Unit tests
behave                    # BDD tests in features/
make ci                   # Run all checks (lint, format, typecheck, test, bdd, pre-commit)

# Coverage
pytest --cov=unifi_network_maps --cov-report=term-missing

# Smoketests (requires live UniFi or mock data)
make smoketest            # Live UniFi
make smoketest-mock       # Mock data
make smoketest-validate   # Validate smoketest output structure

# Visual regression testing
make visual-regression    # Compare SVGs against baselines
make visual-baselines     # Update baseline images after intentional changes

# Mock data generation
make mock-data

# Help
make makefile-help        # Show all make targets
```

## Environment Variables

```bash
UNIFI_URL=https://192.168.1.1
UNIFI_SITE=default
UNIFI_USER=local_admin
UNIFI_PASS=********
UNIFI_VERIFY_SSL=false
UNIFI_REQUEST_TIMEOUT_SECONDS=10
```

## CLI Quick Reference

```bash
# Basic usage
unifi-network-maps --stdout                              # Mermaid to stdout
unifi-network-maps --markdown --output ./network.md     # Markdown file

# Formats
--format mermaid|svg|svg-iso|lldp-md|mkdocs|json|inventory

# Common options
--include-ports          # Show port labels
--include-clients        # Add client nodes (works with all formats including inventory)
--client-scope wired|wireless|all
--only-unifi            # Filter to UniFi devices only
--collapse-clients      # Group clients into cluster nodes
--mock-data FILE        # Use mock JSON instead of API
--direction LR|TB       # Diagram direction
--group-by-type         # Group nodes in subgraphs (Mermaid)
--svg-layout-mode physical|grouped|vlan  # SVG layout mode
--icon-set isometric|modern              # SVG icon set
--theme-file FILE       # Custom theme YAML
--resolve-hostnames / --no-resolve-hostnames  # Reverse DNS lookup
--wan-label LABEL       # WAN upstream ISP label
--wan-speed SPEED       # WAN upstream speed label
```

## Testing

- **Unit tests**: `tests/` - pytest
- **BDD tests**: `features/` - behave
- **Smoketest validation**: `tests/test_smoketest_validation.py` - structural validation of output files
- **Visual regression**: `tests/test_visual_regression.py` - pixel-based SVG comparison
- **Contract tests**: Moved to `unifi-topology` library

## Code Quality Guidelines

From AGENTS.md:

- Clear, intention-revealing names
- Optimize for readability over cleverness
- Small, safe refactors; commit often
- Functions > 15 lines are a code smell
- Max cyclomatic complexity per function: 12 (enforced by CI)
- Typing (pyright strict-compatible)
- No prints in core modules (use `logging`)
- Pure functions where possible

## Key Dependencies

- `unifi-topology` - Model, adapters, SVG rendering (brings `requests`, `python-dotenv`, `dnspython`)
- `PyYAML` - Theme configuration (Mermaid theme parsing)
- `Jinja2` - Template rendering
- `Faker` (dev) - Mock data generation
- `cairosvg` (dev) - SVG to PNG rendering for visual regression
- `Pillow` (dev) - Image comparison for visual regression
- `radon`/`xenon` (dev) - Cyclomatic complexity checks

## Related Projects

- Home Assistant integration: https://github.com/merlijntishauser/unifi-network-maps-ha
