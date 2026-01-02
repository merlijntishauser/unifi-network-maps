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

Basic map (tree layout by LLDP hops):

```bash
python -m unifi_mermaid.cli --stdout
```

Write Markdown for notes tools:

```bash
python -m unifi_mermaid.cli --markdown --output ./network.md
```

Show ports + clients:

```bash
python -m unifi_mermaid.cli --include-ports --include-clients --stdout
```

SVG output (orthogonal layout + icons):

```bash
python -m unifi_mermaid.cli --format svg --output ./network.svg
```

Isometric SVG output:

```bash
python -m unifi_mermaid.cli --format svg-iso --output ./network.svg
```

SVG size overrides:

```bash
python -m unifi_mermaid.cli --format svg --svg-width 1400 --svg-height 900 --output ./network.svg
```

Legend only:

```bash
python -m unifi_mermaid.cli --legend-only --stdout
```

## Options

- `--format mermaid|svg|svg-iso`: output format (default mermaid).
- `--include-ports`: show port labels (Mermaid shows both ends; SVG shows compact labels).
- `--only-unifi`: only include neighbors that are UniFi devices.
- `--direction LR|TB`: diagram direction for Mermaid (default TB).
- `--stdout`: write output to stdout.
- `--markdown`: wrap Mermaid output in a code fence.
- `--group-by-type`: group nodes by gateway/switch/AP in Mermaid subgraphs.
- `--include-clients`: add active wired clients as leaf nodes.
- `--legend-only`: render just the legend as a separate Mermaid graph (Mermaid only).
- `--debug-dump`: dump gateway + sample devices to stderr for debugging.
- `--debug-sample N`: number of non-gateway devices in debug dump (default 2).
- `--svg-width/--svg-height`: override SVG output dimensions.

## Notes

- Default output is top-to-bottom (TB) and rendered as a hop-based tree from the gateway(s).
- Nodes are color-coded by type (gateway/switch/AP/client) with a sensible default palette.
- PoE links are highlighted in blue and annotated with a power icon when detected from `port_table`.
- SVG output uses Material Design Icons for device glyphs.
- Isometric SVG output uses MIT-licensed isometric icons from `richbl/isometric-icons`.
- SVG port labels render inside child nodes for readability.
