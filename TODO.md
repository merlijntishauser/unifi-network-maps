# TODO (Refactor Proposals)

## P0 - Correctness/Clarity
- done

## P1 - Maintainability
- **LLDP ↔ port_table alignment:** Fallback match port `name`/`ifname` when `local_port_idx` is missing.

## P2 - Cleanup/Quality
- **Logging consistency:** Add normalized device/edge counts to logs for easier troubleshooting.
- **Tests for uplink fallback:** Add a fixture covering missing LLDP but present `uplink` data.
