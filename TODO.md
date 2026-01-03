# TODO (Refactor Proposals)

## P0 - Correctness/Clarity
- done

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
