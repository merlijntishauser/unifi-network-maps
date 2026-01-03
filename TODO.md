# TODO (Refactor Proposals)

## P0 - Correctness/Clarity
- **Stabilize topology ordering:** Sort devices/edges by name or MAC before building the tree for deterministic output.

## P1 - Maintainability
- **Expand typed device adapter:** Add explicit fields/models for `port_table`, `uplink`, and `last_uplink`.
- **LLDP ↔ port_table alignment:** Fallback match port `name`/`ifname` when `local_port_idx` is missing.
- **Deduplicate render state:** Remove duplicate `node_port_prefix` declaration in `render_svg`.
- **Shared SVG defs:** Extract common SVG `<defs>` (gradients/icons) into helpers to avoid duplication.

## P2 - Cleanup/Quality
- **Config ergonomics:** Support `--env-file` to load different `.env` files for multiple sites.
- **Mermaid styling config:** Allow configuring PoE link color or style instead of hardcoding.
- **Logging consistency:** Add normalized device/edge counts to logs for easier troubleshooting.
- **Tests for uplink fallback:** Add a fixture covering missing LLDP but present `uplink` data.

## Next
- Consider refining client inclusion (filter by wired, limit count, or group by uplink device).

## Open Source Readiness
- **Release automation:** Add a GitHub Actions release workflow (build + publish on tag).
- **PyPI credentials:** Configure PyPI trusted publisher or token in repo settings.
