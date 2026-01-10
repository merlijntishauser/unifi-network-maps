# Changelog

All notable changes to this project will be documented in this file.

## v1.4.2 (unreleased)
- Added static code analysis and stricter type-checking
- Added contract tests for UniFi API wrapper with fixture-based validation.
- Added optional live UniFi contract tests (gated by `UNIFI_CONTRACT_LIVE=1`).
- Split CI into dedicated jobs and added a contract-test job.
- Added Behave-based BDD tests covering CLI outputs, mkdocs assets, and error handling.
- Added mkdocs timestamp (timezone configurable via `--mkdocs-timestamp-zone`).
- Added optional dual Mermaid blocks for MkDocs Material theme switching (`--mkdocs-dual-theme`).
- Switched UniFi API cache payloads to JSON for safer local storage.
- Skips cache usage when the cache directory is group/world-writable.
- Added `--no-cache` to bypass UniFi API cache reads/writes.
- Added file locking around cache read/write operations to avoid concurrent corruption.
- Hardened Mermaid label escaping for newlines and backslashes.
- Fixed device cache serialization to preserve LLDP data when caching.
- Added optional UniFi API request timeouts via `UNIFI_REQUEST_TIMEOUT_SECONDS`.
- Made `--output` writes atomic to avoid partial files on interruption.

## v1.4.1
- pip install was broken, fixed.

## v1.4.0
- Added MkDocs output, which includes gateway/switch details and per-port tables.
- Port tables show speed, PoE status, power, and wired clients per port.
- Added compact legend with sidebar injection (`--mkdocs-sidebar-legend`).
- LLDP markdown includes the same device details and port tables when enabled.
- Improved uplink labeling (gateway shows Internet for WAN/unknown).
- Aggregated ports are combined into single LAG rows.
- Bumped minimum Python to 3.13 and aligned CI to 3.13.
- Pinned runtime/dev/build dependencies and added `requirements*.txt` + `constraints.txt`.
- Added `--mock-data` for safe, offline rendering from fixtures.
- Added Faker-powered `--generate-mock` for deterministic mock fixtures (dev-only).
- Added mock fixtures + SVG/Mermaid examples, with mock smoketest/CI steps.

## v1.3.1
- Added `lldp-md` output with per-device details tables and optional client sections.
- Added `--client-scope wired|wireless|all` and dashed wireless client links in Mermaid/SVG.
- Expanded smoketest outputs for wireless/all client scopes and LLDP markdown.
- Fixed SVG icon loading paths after package reorg.
- Tuned isometric port label placement on front tiles.

## v1.3.0
- Reorganized package into submodules (`adapters/`, `model/`, `render/`, `io/`, `cli/`).
- YAML-based theming with default + dark themes and `--theme-file`.
- CLI help now grouped by category; CLI logic split into focused helpers.
- Isometric SVG layout constants centralized; extra viewBox padding to avoid clipping.
- LLDP port index fallback matches `port_table` `ifname`/`name`.
- Added PoE/edge/device count logging and improved label ordering helpers.
- Coverage excludes asset packages; docs updated (options/groups + AI disclosure).

## v1.2.4
- Added typed `UplinkInfo`/`PortInfo` and uplink fallback for LLDP gaps.
- Deterministic edge ordering for repeatable output.
- CI publish workflow (trusted publishing) and release docs.
- Project metadata and packaging updated for OSS readiness.

## v1.1.0
- Added isometric SVG output with grid-aligned links and isometric icon set.
- Improved port label placement and client labeling in SVG outputs.
- Added smoketest target with multiple outputs (ports/clients/legend).
- Added UniFi API response caching with TTL.
- Fixed Mermaid legend/grouped output parsing errors.
- Refined visuals: link gradients, tile gradients, icon placement tweaks.

## v1.0.0
- Mermaid legend can render as a separate graph.
- Straight Mermaid links with node type coloring.
- Added wired client leaf nodes and uplink port labels.
- Expanded PoE detection tests and LLDP helpers.
- CLI loads `.env` automatically.

## v0.2.0
- Added versioning workflow and bump tooling.
- Introduced SVG renderer and tree layout fixes.
- Increased test coverage and added coverage tooling.
