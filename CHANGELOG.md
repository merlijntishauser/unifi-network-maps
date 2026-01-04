# Changelog

All notable changes to this project will be documented in this file.

## Unreleased
- TBD.

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
