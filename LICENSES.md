# Third-Party Licenses

This document lists the licenses for third-party assets used in this project.

## Icon Sets

### Isometric Icon Set (Default)

#### markmanx/isopacks (MIT)

Isometric SVG icons in the isometric set are vendored under `src/unifi_network_maps/assets/icons/isometric/`.
The upstream MIT license is included at:

```
src/unifi_network_maps/assets/icons/isometric/ISOPACKS_LICENSE
```

### Modern Icon Set

The modern icon set (`src/unifi_network_maps/assets/icons/modern/`) combines custom isometric
base shapes with Heroicons rendered on top using isometric matrix transforms.

#### Isometric Base Shapes (MIT)

Custom isometric base shapes created for this project, using the isopacks color palette
(#CDD9EE light, #B5C5DC medium, #6885A9 dark, #231F20 outline).

#### Heroicons (MIT)

Icon symbols from [Heroicons](https://heroicons.com/) by Tailwind Labs.

- Source: https://github.com/tailwindlabs/heroicons
- License: MIT License
- Icons used: globe-alt, server, wifi, computer-desktop

| Icon | Base Shape | Heroicon |
|------|------------|----------|
| gateway.svg | Cube | globe-alt |
| switch.svg | 1U rack | server |
| ap.svg | Disc | wifi |
| client.svg | Cube | computer-desktop |
| other.svg | Cube | server |

## Fonts

### Inter (SIL Open Font License 1.1)

The [Inter](https://rsms.me/inter/) typeface by Rasmus Andersson is used in the UniFi and UniFi Dark themes.
Variable WOFF2 files are vendored under `src/unifi_network_maps/assets/fonts/`.

- Source: https://github.com/rsms/inter
- License: SIL Open Font License 1.1
- License file: `src/unifi_network_maps/assets/fonts/INTER_LICENSE`

### Space Grotesk (SIL Open Font License 1.1)

The [Space Grotesk](https://floriankarsten.github.io/space-grotesk/) typeface by Florian Karsten is used in the Minimal theme.
Variable WOFF2 files are vendored under `src/unifi_network_maps/assets/fonts/`.

- Source: https://github.com/floriankarsten/space-grotesk
- License: SIL Open Font License 1.1
- License file: `src/unifi_network_maps/assets/fonts/SPACE_GROTESK_LICENSE`

## License Compatibility

When sourcing icons for this project, use license-compatible sources:

**Compatible licenses:**
- Public Domain / CC0
- MIT License
- Apache 2.0
- CC-BY (with attribution)
- BSD

**Not compatible:**
- CC-NC (Non-Commercial)
- GPL/LGPL (copyleft)
