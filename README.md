# unifi-mermaid-map

Dynamic UniFi -> Mermaid network maps generated from LLDP topology.

## Setup

- Python >= 3.10
- Virtualenv required

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Set environment variables (no secrets in code). The CLI loads `.env` automatically if present:

```bash
export UNIFI_URL=https://192.168.1.1
export UNIFI_SITE=default
export UNIFI_USER=local_admin
export UNIFI_PASS=********
export UNIFI_VERIFY_SSL=false
```

## Usage

```bash
python -m unifi_mermaid.cli --site default --format mermaid --markdown --output ./network.md
```

Options:
- --include-ports
- --only-unifi
- --direction LR|TB
- --stdout
- --markdown
- --group-by-type
- --include-clients
- --legend
- --debug-dump
- --debug-sample N

Notes:
- Default output is top-to-bottom (TB) and rendered as a hop-based tree from the gateway(s).
- `--group-by-type` creates Mermaid subgraphs for gateway/switch/AP nodes.
- `--debug-dump` writes a JSON payload of the gateway and sample devices to stderr.
- `--include-ports` shows both ends when LLDP is available (e.g. `A: Port 1 <-> B: Port 7`).
- `--include-clients` adds active clients as leaf nodes (may clutter large networks).
- Nodes are color-coded by type (gateway/switch/AP/client) with a sensible default palette.
- `--legend` adds a color/PoE legend as a separate subgraph.

## Notes

- The UniFi API integration is stubbed in `src/unifi_mermaid/unifi.py` and should be implemented against `unifi-controller-api`.
- Core modules avoid prints; use logging and the export layer for output.
