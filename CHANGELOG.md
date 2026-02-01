# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[Unreleased]: https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.14...HEAD
[1.4.14]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.11...v1.4.14
[1.4.13]:https://github.com/merlijntishauser/unifi-network-maps/compare/v1.4.11...v1.4.13
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
