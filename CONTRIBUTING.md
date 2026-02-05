# Contributing

Thanks for considering a contribution!

## Project Overview

**unifi-network-maps** is a Python CLI tool that generates network diagrams from UniFi Network Controller data via LLDP topology discovery.

## Architecture

The project follows a clean pipeline architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Data Flow                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │  Source  │───▶│  Model   │───▶│  Render  │───▶│  Export  │             │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘             │
│       │               │               │               │                    │
│  UniFi API       Topology        Mermaid/SVG      Files/                  │
│  Mock data       Devices         MkDocs           stdout                  │
│                  Edges           JSON                                      │
│                  VLANs                                                     │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
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
├── adapters/            # External data sources
│   ├── config.py        # Environment/config loading
│   └── unifi.py         # UniFi API adapter
│
├── model/               # Core domain models
│   ├── topology.py      # Device, Edge, Topology dataclasses
│   ├── clients.py       # Client device handling
│   ├── connection.py    # Wireless connection quality metrics
│   ├── lldp.py          # LLDP neighbor parsing
│   ├── labels.py        # Label generation utilities
│   ├── ports.py         # Port handling and mapping
│   ├── vlans.py         # VLAN inventory management
│   ├── mock.py          # Mock data structures
│   ├── snapshot.py      # Topology serialization
│   └── diff.py          # Topology change detection
│
├── render/              # Output renderers
│   ├── mermaid.py       # Mermaid diagram output
│   ├── mermaid_theme.py # Mermaid theming
│   ├── svg.py           # SVG output (orthogonal + isometric)
│   ├── svg_theme.py     # SVG theming dataclass
│   ├── theme.py         # Theme loading and resolution
│   ├── legend.py        # Legend rendering
│   ├── mkdocs.py        # MkDocs format output
│   ├── lldp_md.py       # LLDP markdown tables
│   └── templating.py    # Jinja2 template utilities
│
├── io/                  # File I/O operations
│   ├── export.py        # File export utilities
│   ├── mock_data.py     # Mock data loading
│   ├── mock_generate.py # Mock data generation (Faker)
│   ├── paths.py         # Path resolution utilities
│   └── debug.py         # Debug dump utilities
│
└── assets/              # Static assets
    ├── icons/           # SVG device icons (isometric, modern, modern-flat)
    └── themes/          # Theme YAML files
```

### Key Concepts

- **Topology**: Collection of `Device` nodes and `Edge` connections
- **Device**: Network device with type, name, MAC, model, ports
- **Edge**: Connection between devices with PoE status, VLAN, port info
- **ConnectionInfo**: Wireless quality metrics (signal, noise, rates)
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
| Contract | `tests/test_contract_unifi.py` | `pytest` | API fixtures |
| Visual | `tests/test_visual_regression.py` | `pytest` | SVG rendering |
| Smoketest | `scripts/smoketest.sh` | `make smoketest-mock` | End-to-end |

Notes:
- Live contract tests require `UNIFI_CONTRACT_LIVE=1` plus UniFi env vars.
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
make makefile-help    # List all targets
```

## Release

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
python -m build
twine upload dist/*
```

See `LICENSES.md` for third-party license info.

## Code Guidelines

- Clear, intention-revealing names
- Small, focused functions (>15 lines is a code smell)
- Type annotations throughout
- No prints in core modules (use `logging`)
- Pure functions where possible
- Add tests for behavior changes
- Run `make ci` before opening a PR

## Related Projects

- **Home Assistant integration**: [unifi-network-maps-ha](https://github.com/merlijntishauser/unifi-network-maps-ha)
  
