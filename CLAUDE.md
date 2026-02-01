# CLAUDE.md

Quick reference for AI assistants working on this codebase.

## Project Overview

**unifi-network-maps** - A Python CLI tool that generates network diagrams (Mermaid, SVG, MkDocs) from UniFi Network Controller data via LLDP topology.

- **Version**: 1.4.14
- **Python**: 3.12+ (3.13 preferred)
- **License**: MIT
- **PyPI**: `pip install unifi-network-maps`

## Architecture

```
Source (UniFi API) → Model (devices/topology) → Diagram (Mermaid/SVG) → Export (files/stdout)
```

### Source Layout

```
src/unifi_network_maps/
├── cli/                 # CLI entry point, argument parsing
│   ├── args.py          # Argument definitions
│   ├── main.py          # Main entry point
│   ├── render.py        # Render dispatch
│   └── runtime.py       # Runtime context
├── adapters/
│   ├── config.py        # Environment/config loading
│   └── unifi.py         # UniFi API adapter
├── model/
│   ├── topology.py      # Core topology model
│   ├── lldp.py          # LLDP parsing
│   ├── labels.py        # Label generation
│   ├── ports.py         # Port handling
│   ├── vlans.py         # VLAN inventory
│   └── mock.py          # Mock data structures
├── render/
│   ├── mermaid.py       # Mermaid output
│   ├── mermaid_theme.py # Mermaid theming
│   ├── svg.py           # SVG output (orthogonal + isometric)
│   ├── svg_theme.py     # SVG theming
│   ├── theme.py         # Theme loading
│   ├── legend.py        # Legend rendering
│   ├── mkdocs.py        # MkDocs format
│   ├── lldp_md.py       # LLDP markdown tables
│   └── templating.py    # Jinja2 templates
├── io/
│   ├── export.py        # File export
│   ├── mock_data.py     # Mock data loading
│   ├── mock_generate.py # Mock generation (uses Faker)
│   └── debug.py         # Debug dump utilities
└── assets/
    ├── icons/           # SVG device icons
    └── themes/          # Default theme YAML files
```

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

# Mock data generation
make mock-data
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
--format mermaid|svg|svg-iso|lldp-md|mkdocs|json

# Common options
--include-ports          # Show port labels
--include-clients        # Add client nodes
--client-scope wired|wireless|all
--only-unifi            # Filter to UniFi devices only
--mock-data FILE        # Use mock JSON instead of API
--direction LR|TB       # Diagram direction
--group-by-type         # Group nodes in subgraphs
--theme-file FILE       # Custom theme YAML
```

## Testing

- **Unit tests**: `tests/` - pytest
- **BDD tests**: `features/` - behave
- **Contract tests**: `tests/test_contract_unifi.py` - fixture-based
- **Live contract tests**: Set `UNIFI_CONTRACT_LIVE=1` with UniFi env vars

## Code Quality Guidelines

From AGENTS.md:
- Clear, intention-revealing names
- Optimize for readability over cleverness
- Small, safe refactors; commit often
- Functions > 15 lines are a code smell
- Typing (mypy-ready)
- No prints in core modules (use `logging`)
- Pure functions where possible

## Key Dependencies

- `unifi-controller-api` - UniFi API wrapper
- `python-dotenv` - Environment loading
- `PyYAML` - Theme configuration
- `Jinja2` - Template rendering
- `Faker` (dev) - Mock data generation

## Related Projects

- Home Assistant integration: https://github.com/merlijntishauser/unifi-network-maps-ha
