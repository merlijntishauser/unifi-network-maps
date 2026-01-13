# Home Assistant Integration POC

Goal: a quick, low-risk proof of concept for a Lovelace UI card + export pipeline, while keeping code separable for a future standalone repo. Updated direction: the HA integration should be a separate repo (TypeScript card + Python integration) that live-queries UniFi data, with credentials managed in the HA UI.

## Scope (POC)
- Export assets to a target HA directory (ex: `/config/www/unifi-network-maps/`):
  - `network.svg` (primary visual)
  - `network.json` (data model for drilldown/UX)
  - `lovelace.yaml` (example card config)
- No HA-specific runtime code in core renderer; just export assets and a schema.
- Keep everything in a separate module (ex: `src/unifi_network_maps/ha/`) to allow easy extraction.
- `--include-clients` should control whether clients appear in `network.json`.
## Future direction (live HA integration)
- Separate repo for the HA integration to align with HA tooling and TS card development.
- Use HA Config Flow to collect UniFi credentials in the UI (no `.env` in HA).
- Store credentials in HA’s config entries/secrets storage.
- Use a `DataUpdateCoordinator` to poll the UniFi API for LLDP + clients and refresh the card.
- Expose rendered SVG + JSON via HA endpoints or cached files, but updated by the integration.

## POC Constraints
- Avoid storing secrets in exported JSON.
- Keep schema stable and explicit for future UI evolution.
- Use mock data for local/dev and CI.

## Proposed Architecture

### Export flow
```
UniFi source -> model -> render -> export
                       \-> HA JSON
                       \-> HA SVG
                       \-> Lovelace config
```

### Data schema (draft)
Top-level keys:
- `devices`: list of devices
- `ports`: list of ports
- `links`: list of links
- `clients`: list of clients (optional)

Suggested fields (minimal):
- `devices`: id, name, type, model, ip, mac
- `ports`: id, device_id, name, poe_status, poe_power_w, speed
- `links`: id, left_device_id, right_device_id, left_port_id, right_port_id, poe
- `clients`: id, name, mac, connected_port, wired

SVG drilldown hooks:
- Device and port nodes include `data-device-id` and `data-port-id`.

## Lovelace Card (POC)
- Minimal custom card stub lives in `docs/ha_card_stub/unifi-network-map.js`.
- Card goal: `type: custom:unifi-network-map` with SVG + JSON-driven drilldown.
- UX goals (future):
  - Pan/zoom SVG.
  - Hover/selection panel showing device + port details.
  - PoE badge(s) for PoE ports and links.

## Separation Strategy
- New module (ex: `src/unifi_network_maps/ha/`):
  - `export.py`: write SVG/JSON/Lovelace outputs
  - `schema.py`: JSON schema helpers
  - `render.py`: svg hooks (if needed), or wrappers over existing renderers
- Keep CLI flags isolated (ex: `--ha-output`) to avoid mixing with core flows.
## HA Integration Architecture (target)
- HA integration repo (Python):
  - `config_flow.py`: UniFi URL, site, user/pass, verify SSL.
  - `coordinator.py`: periodic refresh, error handling, last-success timestamps.
  - `api.py`: thin wrapper around `unifi-controller-api` (or core helpers reused from this repo).
  - `sensor`/`diagnostics`: optional, but keep core logic in coordinator.
- HA custom card repo (TypeScript):
  - Fetch SVG/JSON from HA endpoints (or `/local/` cache).
  - Render SVG with clickable nodes; drilldown panel for device/port/client.

## BDD Scenarios (current)
- Export writes `network.svg` + `network.json`.
- JSON contains keys: `devices, ports, links`.
- Ports include PoE metadata fields.
- Clients include drilldown fields.
- No secrets in JSON.
- `lovelace.yaml` is written and references a custom card.
- SVG includes drilldown data attributes.

## Next steps
1. Confirm JSON schema fields and naming.
2. Decide location of HA module for easy extraction.
3. Implement minimal exporter behind `--ha-output`.
4. Make BDD scenarios pass with mock data.
5. Create HA integration repo skeleton (config flow + coordinator) and TS card stub.
6. Extract to standalone repo when ready.

## Manual test drive (Home Assistant)
1. Generate assets to an HA-accessible folder (example for HA OS):
   ```bash
   unifi-network-maps \\
     --mock-data examples/mock_data.json \\
     --ha-output /config/www/unifi-network-maps \\
     --include-clients
   ```
2. The export now writes `unifi-network-map.js` into the HA output directory.
3. Add the resource in Home Assistant:
   - Settings → Dashboards → Resources → Add resource
   - URL: `/local/unifi-network-maps/unifi-network-map.js`
   - Type: `JavaScript Module`
4. Add a Lovelace card with the custom card config (adjust the `/local/...` path to match your output dir):
   ```yaml
   type: custom:unifi-network-map
   svg_url: /local/unifi-network-maps/network.svg
   data_url: /local/unifi-network-maps/network.json
   ```
5. Validate that the SVG renders and data loads:
   - The card should show the SVG and a “Loaded X devices” status line.
   - Click a device to see basic details in the panel.
   - If `--include-clients` was used, the JSON will include clients for later drilldown.
