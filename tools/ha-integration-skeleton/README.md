# Home Assistant Integration Skeleton

This is a minimal skeleton for a future Home Assistant integration + custom card.
It is intentionally self-contained so it can be split into a standalone repo.

## Structure
- `custom_components/unifi_network_map/`: HA integration (Python).
- `frontend/`: Lovelace custom card (TypeScript).

## Notes
- This is a stub for POC planning only; it does not implement live UniFi queries yet.
- Config Flow + DataUpdateCoordinator are outlined, but not wired to UniFi API.
