# Home Assistant Integration POC

Goal: a quick, low-risk proof of concept for a Lovelace UI card + export pipeline, while keeping code separable for a future standalone repo.

## Scope (POC)
- Export assets to a target HA directory (ex: `/config/www/unifi-network-maps/`):
  - `network.svg` (primary visual)
  - `network.json` (data model for drilldown/UX)
  - `lovelace.yaml` (example card config)
- No HA-specific runtime code in core renderer; just export assets and a schema.
- Keep everything in a separate module (ex: `src/unifi_network_maps/ha/`) to allow easy extraction.
- `--include-clients` should control whether clients appear in `network.json`.

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
- Current state: no custom card shipped yet; use built-in cards to view the SVG.
- Future card goal: `type: custom:unifi-network-map` with SVG + JSON-driven drilldown.
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
5. Extract to standalone repo when ready.

## Manual test drive (Home Assistant)
1. Generate assets to an HA-accessible folder (example for HA OS):
   ```bash
   unifi-network-maps \\
     --mock-data examples/mock_data.json \\
     --ha-output /config/www/unifi-network-maps \\
     --include-clients
   ```
2. In Home Assistant, add a Lovelace card using a built-in card (POC):
   ```yaml
   type: picture
   image: /local/unifi-network-maps/network.svg
   ```
   Or:
   ```yaml
   type: markdown
   content: |
     ![](/local/unifi-network-maps/network.svg)
   ```
3. (Optional) Keep the future custom-card config for later:
   ```yaml
   type: custom:unifi-network-map
   svg_url: /local/unifi-network-maps/network.svg
   data_url: /local/unifi-network-maps/network.json
   ```
4. Validate that the SVG renders and drilldown data loads (future custom card):
  - Hover/selection should show device + port info.
  - If `--include-clients` was used, client drilldowns should appear.
