# unifi-network-maps

CLI tool for generating UniFi network maps from LLDP topology. Outputs Mermaid, SVG (including isometric), Markdown, and MkDocs formats.

## Quick start

```bash
pip install unifi-network-maps
```

```bash
# Mermaid diagram to stdout
unifi-network-maps --stdout

# Isometric SVG to file
unifi-network-maps --format svg-iso --output network.svg

# With clients and port labels
unifi-network-maps --format svg-iso --include-clients --include-ports --output network.svg
```

## Using as a library

The topology model, adapters, diff engine, and SVG renderer live in the
[unifi-topology](https://pypi.org/project/unifi-topology/) library. Use it directly for
programmatic access:

```python
from unifi_topology.model.topology import Topology
from unifi_topology.adapters import Config, fetch_devices
from unifi_topology.render import render_svg
```

See the [unifi-topology documentation](https://github.com/merlijntishauser/unifi-topology)
for the full API.

## API Reference

- [render](api/render.md) -- Mermaid rendering, MkDocs output, theming (CLI-specific)
