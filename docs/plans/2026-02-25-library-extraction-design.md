# Library Extraction Design

## Problem

The project serves three audiences through a single package:

1. **CLI users** -- run `unifi-network-maps --format svg` for a diagram
2. **Home Assistant integration** -- imports adapters, model, and SVG render programmatically
3. **MkDocs documentation sites** -- a niche output format

This creates two problems:

- **HA integration fit**: The HA integration depends on a CLI tool and imports from its internals. It should depend on a library with a stable, intentional API.
- **User confusion**: 7 flat `--format` options make it unclear what the tool actually does. `svg-iso` looks like a separate format rather than a variant of SVG.

## Design

### Two packages, two repositories

Separate repos enforce package boundaries structurally. No import linting or conventions needed -- if `unifi-topology` doesn't have `unifi-network-maps` in its dependencies, it physically cannot import from it.

**`unifi-topology`** (library, new repo, 1.0.0):

- `adapters/` -- UniFi API client, config, DNS resolution
- `model/` -- topology, devices, edges, clients, diff, snapshot, mock
- `render/` -- SVG orthogonal + isometric, theming, icons
- Assets: SVG icons, default theme YAML files

**`unifi-network-maps`** (CLI, existing repo, 2.0.0):

- Depends on `unifi-topology`
- `cli/` -- argument parsing, format dispatch, main entry point
- `render/` -- Mermaid, MkDocs, lldp-md, inventory, device port tables
- `io/` -- file export, mock data loading, path resolution
- Templates: Jinja2 templates for Mermaid legends, MkDocs sections

### Repository: `unifi-topology`

```
unifi-topology/
├── pyproject.toml
├── src/unifi_topology/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dns.py
│   │   ├── unifi.py
│   │   └── unifi_api.py
│   ├── model/
│   │   ├── __init__.py
│   │   ├── topology.py
│   │   ├── topology_coerce.py
│   │   ├── clients.py
│   │   ├── classify.py
│   │   ├── connection.py
│   │   ├── edges.py
│   │   ├── helpers.py
│   │   ├── inventory.py
│   │   ├── lldp.py
│   │   ├── labels.py
│   │   ├── ports.py
│   │   ├── vlans.py
│   │   ├── wan.py
│   │   ├── mock.py
│   │   ├── snapshot.py
│   │   └── diff.py
│   └── render/
│       ├── __init__.py
│       ├── svg.py
│       ├── svg_isometric.py
│       ├── svg_theme.py
│       ├── svg_layout.py
│       ├── svg_edges.py
│       ├── svg_labels.py
│       ├── svg_icons.py
│       ├── svg_wan.py
│       ├── svg_iso_geometry.py
│       ├── svg_iso_nodes.py
│       ├── svg_iso_edges.py
│       └── theme.py
├── assets/
│   ├── icons/
│   └── themes/
└── tests/
```

### Repository: `unifi-network-maps` (post-extraction)

```
unifi-network-maps/
├── pyproject.toml
├── src/unifi_network_maps/
│   ├── __init__.py
│   ├── cli/
│   │   ├── args.py
│   │   ├── main.py
│   │   ├── render.py
│   │   └── runtime.py
│   ├── render/
│   │   ├── mermaid.py
│   │   ├── mermaid_theme.py
│   │   ├── mkdocs.py
│   │   ├── lldp_md.py
│   │   ├── inventory.py
│   │   ├── legend.py
│   │   ├── device_summary.py
│   │   ├── device_ports_md.py
│   │   ├── device_ports_aggregate.py
│   │   ├── markdown_tables.py
│   │   └── templating.py
│   └── io/
│       ├── export.py
│       ├── mock_data.py
│       ├── mock_generate.py
│       ├── mkdocs_assets.py
│       ├── paths.py
│       └── debug.py
├── tests/
├── features/
└── docs/
```

### Public API for `unifi-topology`

```python
# unifi_topology.adapters
Config
fetch_devices(config) -> list[dict]
fetch_clients(config) -> list[dict]
fetch_networks(config) -> list[dict]
resolve_hostnames(devices, clients, dns_server) -> tuple[list, list]

# unifi_topology.model
Device, Edge, TopologyResult
WanInfo, DeviceInfo
build_topology(devices, ...) -> TopologyResult
build_device_inventory(devices) -> list[DeviceInfo]
extract_wan_info(devices, networks) -> WanInfo | None
normalize_devices(raw) -> list[Device]

# unifi_topology.model.diff
Topology
TopologyDiff, TopologyChangeEvent
Topology.from_dict(data) -> Topology
Topology.diff(other) -> TopologyDiff

# unifi_topology.model.mock
MockOptions, generate_mock_payload

# unifi_topology.render
render_svg(topology, theme, options) -> str
render_svg_isometric(topology, theme, options) -> str
SvgTheme, SvgOptions, DEFAULT_SVG_THEME
resolve_themes(paths) -> SvgTheme
```

Internal building blocks (`build_client_edges`, `build_device_index`, `build_node_type_map`, `group_devices_by_type`, `group_nodes_by_vlan`) are not part of the public API. The CLI package imports them directly from submodules.

### CLI simplification

`--format svg-iso` is replaced by `--format svg --isometric`. The format list goes from 7 to 6 and help text groups by intent:

```
Diagram formats:   mermaid (default), svg
Data formats:      json, inventory
Documentation:     mkdocs, lldp-md

SVG options:
  --isometric        Use isometric 3D-style layout instead of orthogonal
```

### Migration

No backward compatibility shim. Clean break:

1. Create `unifi-topology` repo, move adapters + model + SVG render code
2. Ship `unifi-topology` 1.0.0 to PyPI
3. Update `unifi-network-maps` to depend on `unifi-topology`, rewrite imports
4. Ship `unifi-network-maps` 2.0.0
5. Update `unifi-network-maps-ha` imports from `unifi_network_maps.*` to `unifi_topology.*`
6. Coordinated release of all three packages

### Dependencies

**`unifi-topology`** (minimal):
- `requests>=2.31,<3`
- `python-dotenv`
- `PyYAML`
- `dnspython`

**`unifi-network-maps`** (adds):
- `unifi-topology>=1.0.0`
- `Jinja2`

### Test split

Each repo owns its own tests:

- **`unifi-topology`** tests: adapter tests (test_unifi.py, test_unifi_api.py, test_config.py), model tests (test_topology.py, test_edges.py, test_clients.py, etc.), SVG render tests (test_svg.py, test_svg_advanced.py, test_svg_iso.py, test_visual_regression.py), contract tests
- **`unifi-network-maps`** tests: CLI tests (test_cli.py, test_cli_render.py, test_runtime.py), Mermaid/MkDocs render tests, IO tests, BDD features

### Why two repos instead of a monorepo

- **Structural boundary enforcement** -- `unifi-topology` cannot accidentally import `unifi_network_maps` because it's not a dependency
- **Independent CI** -- each repo has its own test suite that proves it works in isolation
- **Clear ownership** -- no ambiguity about where new code belongs
- **Low coordination cost** -- same maintainer controls both repos, library API is small and stable, release cadence is low

### What this does NOT change

- All 7 output formats are preserved (svg-iso becomes a flag, not a removal)
- All CLI flags continue to work (except `--format svg-iso` -> `--format svg --isometric`)
- Mock data generation stays in the CLI package
