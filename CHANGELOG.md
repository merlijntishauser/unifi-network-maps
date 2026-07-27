# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `--icon-set unifi`: the new UniFi icon set from `unifi-topology` 3.1.1, with original artwork
  for all 14 node types (ceiling-disc access points, a drive enclosure for NAS, a device group
  for client clusters). The theme matrix in `examples/themes/` now renders all three icon sets
- `--iso-compact-layout`: for `svg-iso`, pack each hub and its clients into a compact district
  instead of spreading siblings along a single diagonal
- `--iso-route-around-nodes`: for `svg-iso`, route edges around intervening nodes instead of
  always turning on the same axis
- Smoketests (`make smoketest` and `make smoketest-mock`) cover the new icon set and both
  isometric layout options, including the two combined

### Fixed
- Combining `--iso-compact-layout` with `--iso-route-around-nodes` no longer clips an edge at the
  left border ([unifi-topology#69]). The isometric canvas is now expanded to contain routed edge
  corners that fall outside the node bounding box

### Changed
- Bump `unifi-topology` to `>=3.1.2`. The isometric icon set replaces its generated placeholder
  icons (speaker, camera, games console, sensor) with real artwork and normalizes icon viewBoxes,
  which changes isometric output; the visual regression baseline is updated accordingly

[unifi-topology#69]: https://github.com/merlijntishauser/unifi-topology/issues/69

## [2.3.1] - 2026-07-24

### Fixed
- MkDocs port tables now show connected device and client names again ([unifi-topology#67])
  - Bump `unifi-topology` to `>=3.0.2`, which restores connected **device** names in
    `render_device_port_overview` (they were empty under 3.0.0/3.0.1)
  - Thread a client-inclusive `node_names` map into `render_device_port_overview` so connected
    **client** cells resolve to names instead of MACs
  - Add a smoketest-validation guard asserting the Connected column resolves device and client names

[unifi-topology#67]: https://github.com/merlijntishauser/unifi-topology/issues/67

## [2.3.0] - 2026-07-24

### Changed
- **Breaking**: Migrate to `unifi-topology` 3.0.x ([#76])
  - `_apply_client_clustering` reads the fresh `node_types`/`node_names` returned by
    `collapse_client_edges` (now a `CollapsedClientEdges` named tuple) instead of relying on
    in-place mutation, and threads them back through to the SVG renderers
  - Update Mermaid escaping snapshots to native forms (`#quot;`, `<br/>`)
  - Supply display labels for device-type SVG groups (`Gateway`/`Switch`/`AP`/`Other`) now
    that 3.0 renders group labels verbatim instead of title-casing them; VLAN group names
    keep their real case (e.g. `IoT`)
  - Bump minimum `unifi-topology` dependency to `>=3.0.0,<4`

[#76]: https://github.com/merlijntishauser/unifi-network-maps/issues/76

## [2.2.0] - 2026-03-25

### Changed
- **Breaking**: Migrate to MAC-based node identification from `unifi-topology` 2.1.0 ([#62])
  - All internal node identifiers (edges, groups, node type maps) now use normalized MAC addresses instead of device names
  - `node_names` mapping threaded through to all renderers (`render_mermaid`, `render_svg`, `render_svg_isometric`) for display labels
  - `collapse_client_edges` and `build_client_edges` receive `node_names` for label generation
  - Debug dump uses MAC-based device lookup
  - Client grouping in SVG grouped layout derived from `node_types` map instead of raw client dicts
- Bump minimum `unifi-topology` dependency to `>=2.1.0`

[#62]: https://github.com/merlijntishauser/unifi-network-maps/issues/62

## [2.1.1] - 2026-03-18

### Removed
- Remove render compatibility shims that caused pyright `reportPrivateImportUsage` errors; imports now go directly to `unifi-topology`

### Fixed
- Fix pyright type-check failures on `mermaid.py` and `test_lldp_md.py` caused by shim `__getattr__` returning `object`
- Update AGENTS.md, CONTRIBUTING.md, and render README to reflect actual module layout after extraction

## [2.1.0] - 2026-03-17
### Changed
- Move shared Mermaid, LLDP markdown, and device port markdown rendering to `unifi-topology` so this package stays focused on CLI orchestration and MkDocs output
- Load Jinja templates from both `unifi-network-maps` and `unifi-topology` render packages for shared renderer templates
- Bump the minimum `unifi-topology` dependency to `>=1.3.0`

## [2.0.3] - 2026-03-14
### Changed
- Bump `unifi-topology` dependency to >= 1.1.1
- Bump dev dependencies: ruff 0.15.6, Faker 40.8.0, cairosvg 2.9.0, setuptools 82.0.1

### Removed
- Remove mkdocs site and GitHub Pages deployment (now in `unifi-topology`)

## [2.0.2] - 2026-03-04
### Fixed
- Fix dark theme loading failing in CI due to path check

## [2.0.0] - 2026-02-25
### Changed
- **Breaking**: Extract model, adapters, SVG rendering, and assets into the [unifi-topology](https://pypi.org/project/unifi-topology/) library
- This package is now a CLI-only wrapper; programmatic access to topology model, adapters, and SVG rendering should use `unifi-topology` directly
- Replace `unifi-controller-api` and `python-dotenv` direct dependencies with `unifi-topology>=1.0.1`
- Update README, docs, and API reference to point at `unifi-topology` for library usage
- Update AI disclosure to reflect current tooling

### Removed
- Local `model/`, `adapters/`, `assets/` packages (now in `unifi-topology`)
- Local SVG renderer and inventory table renderer (now in `unifi-topology`)
- Contract test infrastructure (marker, Makefile target, CI job) -- moved to `unifi-topology`
- Stale API documentation for `adapters` and `model` modules

## [1.6.4] - 2026-02-24
### Fixed
- Classify UXG-type devices (UXG-Pro, UXG-Max) as gateways instead of "other"

## [1.6.3] - 2026-02-14
### Fixed
- Fix UX7 AP classification: add in_gateway_mode to Device dataclass

## [1.6.2] - 2026-02-11
### Fixed
- Fix UX7 in AP mode misclassified as gateway

## [1.6.1] - 2026-02-11
### Added
- Add client support to `--format inventory` via `--include-clients` with `--client-scope` and `--only-unifi` filtering
- Extract firmware version from UniFi-managed clients (Protect cameras, chimes, doorbells) in inventory output
- Add `build_client_inventory()` to the public API
- Add `ip` and `mac` fields to generated mock client data

## [1.6.0] - 2026-02-10
### Added
- Add device inventory table to MkDocs output with model, IP, hostname, MAC, and firmware
- Add `--resolve-hostnames` / `--no-resolve-hostnames` for reverse DNS hostname resolution via the controller
- Add `DeviceInfo` dataclass and `build_device_inventory()` to the public API
- Add `resolve_hostnames()` adapter using dnspython for PTR lookups
- Add `render_dual()` for producing physical + VLAN-grouped SVGs in a single call (#35)
- Add `--svg-layout-mode vlan` to group SVG nodes by VLAN membership (#34)
- Add WAN upstream visualization to Mermaid output
- Formalize public API with `__all__` exports on adapters, model, and render sub-packages (#37)
- Add API documentation with mkdocstrings and GitHub Pages deployment
- Add docstrings to all public API exports

### Changed
- Refactor: decompose svg.py, svg_isometric.py, and device_ports_md.py into focused sub-modules
- Refactor: relocate `SvgOptions` and shared helpers to leaf modules to eliminate cyclic imports
- Tighten max cyclomatic complexity threshold from 14 to 12
- Export `render_device_inventory_table` from render public API

### Fixed
- Fix eager import of faker (dev-only dependency) via model package init

## [1.5.3] - 2026-02-08
### Fixed
- Fix isometric WAN upstream box clipped by viewBox (#33)

## [1.5.2] - 2026-02-07
### Added
- Detect WAN2 disabled state from network config and add `--wan2-disabled` flag
- Make port label color themeable via `text_secondary` theme property

### Fixed
- Handle 429 (Too Many Requests) from UniFi controller gracefully instead of crashing with a traceback
- Fix PoE icon hidden by tall nodes in isometric view
- Fix port label contrast on dark themes
- Fix isometric port labels showing "local" instead of device name
- Fix bidirectional port labels: use "local" for own port
- Drop redundant local port label for APs
- Fix WAN status detection and Unicode glyph rendering
- Fix WAN1 incorrectly showing as disabled

### Changed
- Use `text_primary` for port labels instead of stroke halo
- Use specific exception types instead of broad `Exception` catches
- Refactor: split long rendering functions into focused helpers
- Refactor: extract generic comparison function in diff.py
- Refactor: reuse `coerce_lldp()` in unifi.py serialization

## [1.5.1] - 2026-02-05
### Fixed
- Skip path security check for built-in themes

## [1.5.0] - 2026-02-05
### Added
- Add wireless connection quality metrics to edge data for Home Assistant integration (#24)
  - Signal strength (dBm), noise floor, TX/RX rates, satisfaction score
  - Automatic quality classification (excellent/good/fair/poor)
- Add `minimal-dark` theme with grayscale monochromatic styling
- Add topology diff API for change detection (#21)
  - New `Topology` class with `to_dict()`, `from_dict()`, and `diff()` methods
  - `compare_topologies()` function for stateless comparison
  - Event-style change list with human-readable descriptions
  - JSON serialization support for persistence and MQTT transmission
- Add SVG grouped layout mode (`--svg-layout-mode grouped`) with visual boundaries for network segments (#19)
- Add VLAN information to edge metadata with color-coded visualization (#20)
- Add `--theme` CLI argument for built-in themes: `unifi`, `unifi-dark`, `minimal`, `classic`, `classic-dark` (#22)
- Add theme properties: background, text colors, status indicators, WAN globe, grid color
- Add WAN upstream visualization with ISP label, link speed, and status indicator (`--wan-label`, `--wan-speed`, `--wan2-label`, `--wan2-speed`)
- Add `--icon-set` CLI argument for selectable icon sets: `isometric`, `modern` (#23)
- Add modern icon set with minimalistic isometric device icons
- Add themeable isometric grid color (`grid_color`) for per-theme floor grid styling
- Add `--max-vlan-colors` and `--include-vlan-legend` options for VLAN visualization
- Add `--collapse-clients` to group clients by uplink into cluster nodes with count badges
- Add theme matrix generator script (`make theme-matrix`) with composite PNG overview
- Theme YAML schema now supports `icon_set` and `grid_color` fields

### Changed
- Align UniFi light/dark themes with official ui.com color palette from techspecs.ui.com/brand
- SVG renderer now uses theme-aware colors for background, text labels, and WAN box
- WAN port detection uses `wan_networkconf_id` field instead of hardcoded port numbers
- Light theme isometric grids use darker grid lines for better contrast (blue-tinted for UniFi, grey for others)

### Removed
- Remove flat (Heroicons) and outline (Lucide) icon sets; consolidate to `isometric` and `modern`

### Fixed
- Normalize gateway WAN port speeds from Gbps to Mbps for correct display (e.g., "10GbE" instead of "10MbE")

## [1.4.15] - 2026-02-01
### Changed
- Displaying of friendly device/model names

### Fixed
- Handle disabled WAN interfaces gracefully (avoid unifi-controller-api model parse errors)

## [1.4.14] - 2026-02-01
### Added
- JSON output with VLAN inventory

### Changed
- Added log message when /tmp can't be resolved

## [1.4.13] - 2026-01-25
### Fixed
- Path Traversal Vulnerability in File Operations
- Cache Directory Symlink Attack vector

### Changed
- Improved escaping in Markdown Output
- Made logging less chatty, moved messages to debug level

## [1.4.12] - 2026-01-21
### Added
- Filter UniFi clients with --only-unifi, and not only neighbors

### Fixed
- inconsistencies in --only-unifi

## [1.4.11] - 2026-01-19
### Added
- Add data-edge-left/right attributes to SVG paths

### Fixed
- Regression in identifying wireless/wired clients

## [1.4.10] - 2026-01-18
### Added
- Add speed and channel fields to Edge dataclass

## [1.4.9] - 2026-01-15
### Changed
- Declared support for Python 3.12+ (3.13 preferred) and added CI coverage for 3.12.
- CI now runs on version tags to unblock publish workflow.
- Publish now runs directly on tag pushes; CI runs on all branch pushes.

## [1.4.8] - 2026-01-15
### Yanked
- Release tag repointed after PyPI artifacts were already published.

## [1.4.7] - 2026-01-15
### Changed
- Merged PR #8: https://github.com/merlijntishauser/unifi-network-maps/pull/8

## [1.4.6] - 2026-01-15
### Added
- Home Assistant docs pointing to the standalone integration repo.

### Changed
- Home Assistant integration work moved to `unifi-network-maps-ha`; core repo focuses on renderer + CLI.

### Removed
- HA POC export module, CLI flag, BDD scenarios, and smoketest outputs (now in the HA repo).

### Fixed
- BDD theme-file scenario
- SVG links render correctly for vertically stacked nodes.
- Publish workflow now checks out the tagged source before building.

## [1.4.5] - 2026-01-11
### Added
- Jinja2 templating for MkDocs output, Mermaid legend blocks, and Markdown sections.
- MkDocs sidebar assets and legend HTML blocks moved into reusable templates.
- BDD scenarios for module/console entrypoints plus additional CLI validation errors.

### Changed
- Refactored CLI orchestration into focused CLI/render/runtime modules.
- Extracted MkDocs rendering and sidebar asset output into dedicated modules.
- Moved mock generation into the model layer with a thin IO facade.
- Centralized legend rendering helpers and shared markdown table utilities.
- Publish workflow now runs only after successful tagged CI.
- Added explicit workflow permissions to CI/CodeQL workflows.

### Fixed
- CLI error handling for invalid theme file paths.

### Security
- Enabled Jinja2 autoescaping for HTML templates and marked trusted HTML blocks safe.

## [1.4.4] - 2026-01-11
### Added
- Added smoke tests for dual-theme MkDocs sidebar legend output.

### Changed
- Improved dark theme Mermaid readability (labels + link borders).

### Fixed
- MkDocs sidebar legend duplication with dual-theme output.

## [1.4.2] - 2026-01-10
### Added
- Static code analysis and stricter type-checking.
- Contract tests for UniFi API wrapper with fixture-based validation.
- Optional live UniFi contract tests (gated by `UNIFI_CONTRACT_LIVE=1`).
- Split CI into dedicated jobs and added a contract-test job.
- Behave-based BDD tests covering CLI outputs, mkdocs assets, and error handling.
- Mkdocs timestamp (timezone configurable via `--mkdocs-timestamp-zone`).
- Optional dual Mermaid blocks for MkDocs Material theme switching (`--mkdocs-dual-theme`).
- `--no-cache` to bypass UniFi API cache reads/writes.
- File locking around cache read/write operations to avoid concurrent corruption.
- Optional UniFi API request timeouts via `UNIFI_REQUEST_TIMEOUT_SECONDS`.
- Made `--output` writes atomic to avoid partial files on interruption.

### Changed
- Switched UniFi API cache payloads to JSON for safer local storage.
- Skips cache usage when the cache directory is group/world-writable.

### Fixed
- Hardened Mermaid label escaping for newlines and backslashes.
- Device cache serialization to preserve LLDP data when caching.

## [1.4.1] - 2026-01-06
### Fixed
- Fixed pip install failure.

## [1.4.0] - 2026-01-06
### Added
- MkDocs output with gateway/switch details and per-port tables.
- Port tables show speed, PoE status, power, and wired clients per port.
- Compact legend with sidebar injection (`--mkdocs-sidebar-legend`).
- LLDP markdown includes the same device details and port tables when enabled.
- `--mock-data` for safe, offline rendering from fixtures.
- Faker-powered `--generate-mock` for deterministic mock fixtures (dev-only).
- Mock fixtures + SVG/Mermaid examples, with mock smoketest/CI steps.

### Changed
- Improved uplink labeling (gateway shows Internet for WAN/unknown).
- Aggregated ports are combined into single LAG rows.
- Bumped minimum Python to 3.13 and aligned CI to 3.13.
- Pinned runtime/dev/build dependencies and added `requirements*.txt` + `constraints.txt`.

## [1.3.1] - 2026-01-04
### Added
- `lldp-md` output with per-device details tables and optional client sections.
- `--client-scope wired|wireless|all` and dashed wireless client links in Mermaid/SVG.
- Expanded smoketest outputs for wireless/all client scopes and LLDP markdown.

### Fixed
- Fixed SVG icon loading paths after package reorg.

### Changed
- Isometric port label placement on front tiles.

## [1.3.0] - 2026-01-04
### Added
- YAML-based theming with default + dark themes and `--theme-file`.

### Changed
- Reorganized package into submodules (`adapters/`, `model/`, `render/`, `io/`, `cli/`).
- CLI help now grouped by category; CLI logic split into focused helpers.
- Isometric SVG layout constants centralized; extra viewBox padding to avoid clipping.
- LLDP port index fallback matches `port_table` `ifname`/`name`.
- Added PoE/edge/device count logging and improved label ordering helpers.
- Coverage excludes asset packages; docs updated (options/groups + AI disclosure).

## [1.2.4] - 2026-01-03
### Added
- Typed `UplinkInfo`/`PortInfo` and uplink fallback for LLDP gaps.
- CI publish workflow (trusted publishing) and release docs.
- Project metadata and packaging updated for OSS readiness.

### Changed
- Deterministic edge ordering for repeatable output.

## [1.1.0] - 2026-01-03
### Added
- Isometric SVG output with grid-aligned links and isometric icon set.
- Smoketest target with multiple outputs (ports/clients/legend).
- UniFi API response caching with TTL.

### Changed
- Improved port label placement and client labeling in SVG outputs.
- Refined visuals: link gradients, tile gradients, icon placement tweaks.

### Fixed
- Mermaid legend/grouped output parsing errors.

## [1.0.0] - 2025-12-30
### Added
- Mermaid legend can render as a separate graph.
- Straight Mermaid links with node type coloring.
- Wired client leaf nodes and uplink port labels.
- CLI loads `.env` automatically.

## [0.2.0] - 2026-01-02
### Added
- Versioning workflow and bump tooling.
- Introduced SVG renderer and tree layout fixes.
- Increased test coverage and added coverage tooling.

[Unreleased]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.3.1...HEAD
[2.3.1]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.0.3...v2.1.0
[2.0.3]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.0.2...v2.0.3
[2.0.2]: https://github.com/merlijntishauser/unifi-network-maps/compare/v2.0.0...v2.0.2
[2.0.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.6.4...v2.0.0
[1.6.4]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.6.3...v1.6.4
[1.6.3]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.5.3...v1.6.0
[1.5.3]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.5.2...v1.5.3
[1.5.2]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.15...v1.5.0
[1.4.15]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.14...v1.4.15
[1.4.14]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.13...v1.4.14
[1.4.13]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.12...v1.4.13
[1.4.12]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.11...v1.4.12
[1.4.11]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.10...v1.4.11
[1.4.10]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.9...v1.4.10
[1.4.9]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.8...v1.4.9
[1.4.8]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.7...v1.4.8
[1.4.7]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.6...v1.4.7
[1.4.6]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.5...v1.4.6
[1.4.5]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.4...v1.4.5
[1.4.4]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.2...v1.4.4
[1.4.2]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.1...v1.4.2
[1.4.1]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.0...v1.4.1
[1.4.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.3.1...v1.4.0
[1.3.1]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.2.4...v1.3.0
[1.2.4]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.1.0...v1.2.4
[1.1.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/merlijntishauser/unifi-network-maps/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/merlijntishauser/unifi-network-maps/releases/tag/v0.2.0
