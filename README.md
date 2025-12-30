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

Set environment variables (no secrets in code):

```bash
export UNIFI_URL=https://192.168.1.1
export UNIFI_SITE=default
export UNIFI_USER=local_admin
export UNIFI_PASS=********
export UNIFI_VERIFY_SSL=false
```

## Usage

```bash
python -m unifi_mermaid.cli --site default --format mermaid --output ./network.md
```

Options:
- --include-ports
- --only-unifi
- --direction LR|TB
- --stdout

## Notes

- The UniFi API integration is stubbed in `src/unifi_mermaid/unifi.py` and should be implemented against `unifi-controller-api`.
- Core modules avoid prints; use logging and the export layer for output.
