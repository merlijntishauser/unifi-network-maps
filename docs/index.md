# unifi-network-maps

Generate network diagrams (SVG, Mermaid, MkDocs) from UniFi Network Controller data via LLDP topology.

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

```python
from unifi_network_maps.adapters import Config, fetch_devices, fetch_clients, fetch_networks
from unifi_network_maps.model import (
    build_topology,
    build_client_edges,
    build_node_type_map,
    normalize_devices,
)
from unifi_network_maps.render import render_svg_isometric, SvgOptions

config = Config(url="https://192.168.1.1", site="default", user="admin", password="secret")

raw_devices = fetch_devices(config)
devices = normalize_devices(raw_devices)
topology = build_topology(devices)

node_types = build_node_type_map(devices, topology.tree_edges)
svg = render_svg_isometric(
    topology.tree_edges,
    node_types=node_types,
    options=SvgOptions(layout_mode="grouped"),
)
```

## API Reference

- [adapters](api/adapters.md) -- Configuration, UniFi API, DNS resolution
- [model](api/model.md) -- Topology building, device normalization, client edges
- [render](api/render.md) -- SVG rendering, theming, inventory tables
