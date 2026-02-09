# API Reference

The public API is organized into three packages:

| Package | Purpose |
|---------|---------|
| [`adapters`](adapters.md) | UniFi controller communication, configuration, DNS resolution |
| [`model`](model.md) | Topology building, device normalization, client edges, VLAN grouping |
| [`render`](render.md) | SVG diagram rendering, theming, inventory tables |

All public symbols are available via package-level imports:

```python
from unifi_network_maps.adapters import Config, fetch_devices
from unifi_network_maps.model import Device, Edge, build_topology
from unifi_network_maps.render import render_svg, SvgOptions
```
