# AGENTS.md

##Top priority (XP values)
- Naming is critical; choose clear, intention-revealing names.
- Optimize for human readability and understandability over cleverness.
- Prefer small, safe refactors and commit often.
- Long functions/methods (>15 lines) are a code smell; split into smaller parts.


## Project
Dynamic UniFi → Mermaid Network Maps

Dit project genereert automatisch netwerkdiagrammen (Mermaid) op basis van UniFi Network data (LLDP/topologie).
De output is bedoeld voor:
- Home Assistant (Markdown / Lovelace / filesensor)
- Notes / documentation (Markdown, Obsidian, GitHub, etc.)

Doel: één bron van waarheid, altijd actuele netwerkkaart, zonder handmatig tekenen.

---

## Architectuur-overzicht

Bron → Model → Diagram → Export

1. **Bron**
   - UniFi Network Controller (UniFi OS)
   - API via Python wrapper
   - LLDP als primaire topologiebron

2. **Model**
   - Devices (gateway, switches, AP’s)
   - Interfaces / poorten
   - LLDP neighbors (device ↔ device)
   - (Later uitbreidbaar met clients, VLANs, locaties)

3. **Diagram**
   - Mermaid `graph LR`
   - Unidirectionele of gededupliceerde edges
   - Optioneel poortlabels

4. **Export**
   - `.md` bestand (notes project)
   - `.mermaid` of `.md` voor Home Assistant
   - STDOUT (voor piping / automation)

---

## Technologiekeuze

### Python
- Python ≥ 3.10
- Virtualenv verplicht

### UniFi API
Gebruik **unifi-controller-api** (tnware):
- Abstraheert UniFi OS login
- Mapt responses naar typed objecten
- Bevat `LLDPEntry` objecten (geen raw JSON parsing)

Install:
```bash
pip install unifi-controller-api
```

---

## Configuratie

Gebruik environment variables (geen secrets in code):

```bash
UNIFI_URL=https://192.168.1.1
UNIFI_SITE=default
UNIFI_USER=local_admin
UNIFI_PASS=********
UNIFI_VERIFY_SSL=false
```

---

## Minimale datastructuren

### Device
- name
- model_name
- mac
- ip
- type (gateway / switch / ap)
- lldp_info: list[LLDPEntry]

### LLDPEntry
- chassis_id (meestal MAC)
- port_id
- port_desc (optioneel)

---

## Kernlogica (conceptueel)

1. Login op UniFi Controller
2. Haal alle site devices op (`detailed=True`)
3. Bouw index:
   - `mac → device_name`
4. Loop devices:
   - Voor elke `LLDPEntry`
   - Match neighbor `chassis_id` tegen bekende MAC’s
5. Bouw edges:
   - Deduplicate (A—B == B—A)
   - Voeg optioneel poortlabels toe
6. Render Mermaid

---

## Debug findings (device data)

From recent `--debug-dump` samples:
- `port_table` entries include `port_idx`, `name` (e.g., "Port 2"), `ifname` (e.g., "eth1"), `is_uplink`, and `last_connection.mac`.
- PoE is detectable per port: `poe_enable`, `poe_power`, `port_poe`, `poe_class`, `poe_good`, `poe_voltage`, `poe_current`.
- LLDP entries include `local_port_idx`, `local_port_name`, and `port_id` (often remote port label).
- Devices also expose `uplink` / `last_uplink` with `uplink_device_name` and `uplink_remote_port`.

---

## Mermaid output (voorbeeld)

```mermaid
graph LR
  "Cloud Gateway" ---|"Port 9"| "Core Switch"
  "Core Switch" ---|"Port 3"| "AP Woonkamer"
  "Core Switch" ---|"Port 7"| "AP Zolder"
```

Richtlijnen:
- Gebruik **namen**, niet MAC’s, in diagrammen
- Houd diagram leesbaar (geen clients standaard)
- Eén edge per fysieke link

---

## Bestandsstructuur (voorgesteld)

```text
unifi-mermaid-map/
├── agents.md
├── pyproject.toml
├── src/
│   ├── unifi_mermaid/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── unifi.py
│   │   ├── topology.py
│   │   ├── mermaid.py
│   │   └── export.py
│   └── cli.py
└── README.md
```

---

## CLI-gedrag

Voorbeeld:

```bash
python -m unifi_mermaid.cli \
  --site default \
  --format mermaid \
  --output ./network.md
```

Opties:
- `--include-ports`
- `--only-unifi`
- `--direction LR|TB`
- `--stdout`

---

## Home Assistant integratie

Ondersteun één of meer van:
- Bestand schrijven in `/config/www/`
- Markdown card met `!include`
- Command-line sensor die Mermaid Markdown ophaalt
- Git pull vanuit notes repo

Geen HA-specifieke logica in core code; exportlaag abstraheert dit.

---

## Niet-doelen (bewust)

- Geen SNMP discovery
- Geen realtime updates
- Geen visuele styling buiten Mermaid

---

## Uitbreidingen (later)

- Groeperen per ruimte / verdieping
- VLAN overlays
- Clients als subgraphs
- Export naar Graphviz / draw.io
- NetBox sync

---

## Code quality

- Typing (mypy-ready)
- Geen prints in core modules
- Pure functies waar mogelijk
- Logging via `logging`
- Fail fast bij ontbrekende LLDP

---

## Ontwerpregel

De netwerkkaart moet automatisch correct blijven, ook als niemand eraan denkt.
