# unifi-network-maps

Dynamic UniFi -> Mermaid network maps generated from LLDP topology.

## Setup

- Python >= 3.10
- Virtualenv required

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Local install (non-editable):

```bash
pip install .
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

Use a custom env file:

```bash
unifi-network-maps --env-file ./site.env --stdout
```

## Usage

Basic map (tree layout by LLDP hops):

```bash
unifi-network-maps --stdout
```

Write Markdown for notes tools:

```bash
unifi-network-maps --markdown --output ./network.md
```

Show ports + clients:

```bash
unifi-network-maps --include-ports --include-clients --stdout
```

SVG output (orthogonal layout + icons):

```bash
unifi-network-maps --format svg --output ./network.svg
```

Isometric SVG output:

```bash
unifi-network-maps --format svg-iso --output ./network.svg
```

SVG size overrides:

```bash
unifi-network-maps --format svg --svg-width 1400 --svg-height 900 --output ./network.svg
```

Legend only:

```bash
unifi-network-maps --legend-only --stdout
```

## Local install check

```bash
pip install .
```

## Release

Build and upload to PyPI:

```bash
python -m pip install build twine
python -m build
twine upload dist/*
```

Tagging is recommended before release:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

See `LICENSES.md` for third-party license info.

## Options

The CLI groups options by category (`Source`, `Functional`, `Mermaid`, `SVG`, `Output`, `Debug`).

Source:
- `--site`: override `UNIFI_SITE`.
- `--env-file`: load environment variables from a specific `.env` file.

Functional:
- `--include-ports`: show port labels (Mermaid shows both ends; SVG shows compact labels).
- `--include-clients`: add active wired clients as leaf nodes.
- `--only-unifi`: only include neighbors that are UniFi devices.

Mermaid:
- `--direction LR|TB`: diagram direction for Mermaid (default TB).
- `--group-by-type`: group nodes by gateway/switch/AP in Mermaid subgraphs.
- `--legend-only`: render just the legend as a separate Mermaid graph (Mermaid only).

SVG:
- `--svg-width/--svg-height`: override SVG output dimensions.
- `--theme-file`: load a YAML theme for Mermaid + SVG colors (see `examples/theme.yaml` and `examples/theme-dark.yaml`).

Output:
- `--format mermaid|svg|svg-iso`: output format (default mermaid).
- `--stdout`: write output to stdout.
- `--markdown`: wrap Mermaid output in a code fence.

Debug:
- `--debug-dump`: dump gateway + sample devices to stderr for debugging.
- `--debug-sample N`: number of non-gateway devices in debug dump (default 2).

## Notes

- Default output is top-to-bottom (TB) and rendered as a hop-based tree from the gateway(s).
- Nodes are color-coded by type (gateway/switch/AP/client) with a sensible default palette.
- PoE links are highlighted in blue and annotated with a power icon when detected from `port_table`.
- SVG output uses vendored device glyphs from `src/unifi_network_maps/assets/icons`.
- Isometric SVG output uses MIT-licensed icons from `markmanx/isopacks`.
- SVG port labels render inside child nodes for readability.

## AI Disclosure

This project used OpenAI Codex as a coding assistant for portions of the implementation and documentation.

## Theme file

Example theme YAML (override only the values you want):

```yaml
mermaid:
  nodes:
    gateway:
      fill: "#ffe3b3"
      stroke: "#d98300"
  poe_link: "#1e88e5"
svg:
  links:
    standard:
      from: "#2ecc71"
      to: "#1b8f4a"
    poe:
      from: "#1e88e5"
      to: "#0d47a1"
  nodes:
    switch:
      from: "#d6ecff"
      to: "#b6dcff"
```

The built-in themes live at `src/unifi_network_maps/assets/themes/default.yaml` and
`src/unifi_network_maps/assets/themes/dark.yaml`.
