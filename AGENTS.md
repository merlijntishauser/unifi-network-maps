# AGENTS.md

## Top priority (XP values)
- Naming is critical; choose clear, intention-revealing names.
- Optimize for human readability and understandability over cleverness.
- Prefer small, safe refactors and commit often.
- Long functions/methods (>15 lines) are a code smell; split into smaller parts.


## Project
UniFi Network Maps (core renderer + exporters)

This project automatically generates network diagrams (Mermaid) from UniFi Network data (LLDP/topology).
The output is intended for:
- Home Assistant (POC export assets; live integration lives in separate repo)
- Notes / documentation (Markdown, Obsidian, GitHub, etc.)

Goal: a single source of truth, always up-to-date network maps, without manual drawing.

---

## Architecture overview

Source → Model → Diagram → Export

1. **Source**
   - UniFi Network Controller (UniFi OS)
   - API via Python wrapper
   - LLDP as primary topology source

2. **Model**
   - Devices (gateway, switches, APs)
   - Interfaces / ports
   - LLDP neighbors (device ↔ device)
   - (Extensible later with clients, VLANs, locations)

3. **Diagram**
   - Mermaid `graph TB`
   - Unidirectional or deduplicated edges
   - Optional port labels

4. **Export**
   - `.md` file (notes project)
   - `.mermaid` or `.md` for Home Assistant
   - HA POC assets (SVG + JSON + lovelace.yaml)
   - STDOUT (for piping / automation)

---

## Technology choices

### Python
- Python ≥ 3.13
- Virtualenv required

### UniFi API
Use **unifi-controller-api** (tnware):
- Abstracts UniFi OS login
- Maps responses to typed objects
- Includes `LLDPEntry` objects (no raw JSON parsing)

Install:
```bash
pip install unifi-controller-api
```

### Icons
- Isometric SVG icons are sourced from **markmanx/isopacks** (MIT).

---

## Configuration

Use environment variables (no secrets in code):

```bash
UNIFI_URL=https://192.168.1.1
UNIFI_SITE=default
UNIFI_USER=local_admin
UNIFI_PASS=********
UNIFI_VERIFY_SSL=false
```

---

## Minimal data structures

### Device
- name
- model_name
- mac
- ip
- type (gateway / switch / ap)
- lldp_info: list[LLDPEntry]

### LLDPEntry
- chassis_id (usually MAC)
- port_id
- port_desc (optional)

---

## Core logic (conceptual)

1. Login to UniFi Controller
2. Fetch all site devices (`detailed=True`)
3. Build index:
   - `mac → device_name`
4. Loop devices:
   - For each `LLDPEntry`
   - Match neighbor `chassis_id` against known MACs
5. Build edges:
   - Deduplicate (A—B == B—A)
   - Optionally add port labels
6. Render Mermaid

---

## Debug findings (device data)

From recent `--debug-dump` samples:
- `port_table` entries include `port_idx`, `name` (e.g., "Port 2"), `ifname` (e.g., "eth1"), `is_uplink`, and `last_connection.mac`.
- PoE is detectable per port: `poe_enable`, `poe_power`, `port_poe`, `poe_class`, `poe_good`, `poe_voltage`, `poe_current`.
- LLDP entries include `local_port_idx`, `local_port_name`, and `port_id` (often remote port label).
- Devices also expose `uplink` / `last_uplink` with `uplink_device_name` and `uplink_remote_port`.

---

## Mermaid output (example)

```mermaid
graph TB
  "Cloud Gateway" ---|"Port 9"| "Core Switch"
  "Core Switch" ---|"Port 3"| "AP Woonkamer"
  "Core Switch" ---|"Port 7"| "AP Zolder"
```

Guidelines:
- Use **names**, not MACs, in diagrams
- Keep diagrams readable (no clients by default)
- One edge per physical link

---

## File structure (overview)

```text
unifi-network-map/
├── agents.md
├── pyproject.toml
├── src/
│   ├── unifi_network_maps/
│   │   ├── __init__.py
│   │   ├── adapters/
│   │   │   ├── config.py
│   │   │   └── unifi.py
│   │   ├── model/
│   │   │   ├── topology.py
│   │   │   ├── lldp.py
│   │   │   ├── labels.py
│   │   │   └── ports.py
│   │   ├── render/
│   │   │   ├── mermaid.py
│   │   │   ├── mermaid_theme.py
│   │   │   ├── svg.py
│   │   │   ├── svg_theme.py
│   │   │   └── theme.py
│   │   ├── io/
│   │   │   ├── debug.py
│   │   │   ├── mock_data.py
│   │   │   ├── mock_generate.py
│   │   │   └── export.py
│   │   └── assets/
│   │       └── icons/
│   └── cli.py
└── README.md
```

---

## CLI behavior

Example:

```bash
unifi-network-maps \
  --site default \
  --format mermaid \
  --output ./network.md
```

Options:
Source:
- `--site`
- `--env-file`
- `--mock-data`

Mock:
- `--generate-mock`
- `--mock-seed`
- `--mock-switches`
- `--mock-aps`
- `--mock-wired-clients`
- `--mock-wireless-clients`

Functional:
- `--include-ports`
- `--include-clients`
- `--client-scope wired|wireless|all`
- `--only-unifi`
- `--no-cache`

Mermaid:
- `--direction LR|TB`
- `--group-by-type`
- `--legend-style`
- `--legend-scale`
- `--legend-only`

SVG:
- `--svg-width/--svg-height`
- `--theme-file`

Output:
- `--format mermaid|svg|svg-iso|lldp-md|mkdocs`
- `--markdown`
- `--stdout`
- `--mkdocs-sidebar-legend`
- `--mkdocs-dual-theme`
- `--mkdocs-timestamp-zone`
- `--ha-output`

Debug:
- `--debug-dump`
- `--debug-sample`

---

## Home Assistant integration

Current scope here is export assets only (POC):
- Write SVG + JSON + lovelace.yaml to `/config/www/` or a target folder.

Live updates + credentials via HA UI are planned for a separate HA repo:
- Config Flow collects UniFi credentials.
- DataUpdateCoordinator polls UniFi for LLDP + clients.
- Custom TS card consumes HA endpoints or cached assets.

---

## Non-goals (intentional, for core renderer)

- No SNMP discovery
- No realtime updates (handled in HA integration repo)
- No realtime interactive updates (handled by UI consumers)

---

## Future extensions

- Grouping by room / floor
- VLAN overlays
- Clients as subgraphs
- Export to Graphviz / draw.io
- NetBox sync

---

## Code quality

- Typing (mypy-ready)
- No prints in core modules
- Pure functions where possible
- Logging via `logging`
- Fail fast on missing LLDP
- BDD tests live in `features/` and run via `behave`.
- Contract tests live in `tests/test_contract_unifi.py` with optional live tests gated by `UNIFI_CONTRACT_LIVE=1`.

---

## Design rule

The network map must stay correct automatically, even if nobody thinks about it.
