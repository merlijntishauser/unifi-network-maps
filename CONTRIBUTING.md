# Contributing

Thanks for considering a contribution!

## Project Overview

**unifi-network-maps** is a Python CLI tool that generates network diagrams from UniFi Network Controller data via LLDP topology discovery. It depends on the [unifi-topology](https://github.com/merlijntishauser/unifi-topology) library for the topology model, adapters, and SVG rendering.

## Architecture

```
unifi-topology (library)          unifi-network-maps (CLI)
  Model, Adapters, SVG render  ->   Mermaid, MkDocs, CLI, File I/O
```

### Module Structure

```
src/unifi_network_maps/
├── cli/                 # CLI entry point
│   ├── args.py          # Argument definitions
│   ├── main.py          # Entry point, orchestration
│   ├── render.py        # Render dispatch logic
│   └── runtime.py       # Runtime context management
│
├── render/              # CLI-only output renderers
│   ├── __init__.py      # Re-exports from unifi_topology.render
│   ├── mermaid.py       # Mermaid diagram output
│   ├── mermaid_theme.py # Mermaid theming
│   ├── theme.py         # Theme loading + library SVG delegation
│   ├── legend.py        # Legend rendering
│   ├── mkdocs.py        # MkDocs format output
│   ├── lldp_md.py       # LLDP markdown tables
│   ├── device_summary.py    # Device summary sections
│   ├── device_ports_md.py   # Device port markdown
│   ├── device_ports_aggregate.py # Aggregated port tables
│   ├── markdown_tables.py   # Generic markdown table helpers
│   ├── templating.py    # Jinja2 template utilities
│   └── templates/       # Jinja2 template files
│
└── io/                  # File I/O operations
    ├── export.py        # File export utilities
    ├── mock_data.py     # Mock data loading
    ├── mock_generate.py # Mock data generation (Faker)
    ├── mkdocs_assets.py # MkDocs sidebar asset writing
    ├── paths.py         # Path resolution utilities
    └── debug.py         # Debug dump utilities
```

Topology model, adapters, SVG rendering, and assets live in `unifi-topology`. See the [unifi-topology repo](https://github.com/merlijntishauser/unifi-topology) for contributions to those areas.

### Key Concepts

- **Topology**: Collection of `Device` nodes and `Edge` connections (from `unifi-topology`)
- **Device**: Network device with type, name, MAC, model, ports (from `unifi-topology`)
- **Edge**: Connection between devices with PoE status, VLAN, port info (from `unifi-topology`)
- **Theme**: Visual styling for both Mermaid and SVG output

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
pip install -r requirements-dev.txt -c constraints.txt
pre-commit install
```

Editable install:

```bash
pip install -e .
```

## Running Checks

```bash
ruff check .          # Linting
ruff format .         # Formatting
pyright               # Type checking
pytest                # Unit tests
behave                # BDD tests
```

Or run everything with:

```bash
make ci
```

### Testing Overview

| Type | Location | Command | Purpose |
|------|----------|---------|---------|
| Unit | `tests/` | `pytest` | Core logic |
| BDD | `features/` | `behave` | User scenarios |
| Visual | `tests/test_visual_regression.py` | `pytest` | SVG rendering |
| Smoketest | `scripts/smoketest.sh` | `make smoketest-mock` | End-to-end |

Notes:
- Visual regression uses `cairosvg` + `Pillow` for pixel comparison.
- Update visual baselines with `make visual-baselines` after intentional changes.

## Useful Make Targets

```bash
make ci               # Run all checks
make smoketest-mock   # End-to-end with mock data
make visual-regression # Compare SVG output
make visual-baselines # Update baseline images
make theme-matrix     # Generate theme preview image
make mock-data        # Generate mock JSON
```

## Release

Releases are automated. Pushing a version tag triggers the publish workflow:

```bash
make version-bump     # Bump version, commit, tag, push
```

The GitHub Actions publish workflow builds and uploads to PyPI automatically on tag push. See [RELEASING.md](RELEASING.md) for the full checklist.

## Code Guidelines

- Clear, intention-revealing names
- Small, focused functions (>15 lines is a code smell)
- Type annotations throughout
- No prints in core modules (use `logging`)
- Pure functions where possible
- Add tests for behavior changes
- Run `make ci` before opening a PR

## Related Projects

- **unifi-topology library**: [unifi-topology](https://github.com/merlijntishauser/unifi-topology)
- **Home Assistant integration**: [unifi-network-maps-ha](https://github.com/merlijntishauser/unifi-network-maps-ha)
