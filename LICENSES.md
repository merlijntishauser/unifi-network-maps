# Third-Party Licenses

This document lists the licenses for third-party assets used in this project.

## Icon Sets

### Legacy Icon Set (Default)

#### markmanx/isopacks (MIT)

Isometric SVG icons in the legacy set are vendored under `src/unifi_network_maps/assets/icons/isometric/`.
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

### Flat Icon Set

The flat icon set (`src/unifi_network_maps/assets/icons/flat/`) uses Heroicons outline style.

#### Heroicons Outline (MIT)

Icon symbols from [Heroicons](https://heroicons.com/) by Tailwind Labs.

- Source: https://github.com/tailwindlabs/heroicons
- License: MIT License
- Style: Outline (stroke-based, no fill)

| Icon | Heroicon |
|------|----------|
| gateway.svg | globe-alt (outline) |
| switch.svg | server-stack (outline) |
| ap.svg | wifi (outline) |
| client.svg | computer-desktop (outline) |
| other.svg | server (outline) |
| camera.svg | video-camera (outline) |
| tv.svg | tv (outline) |
| phone.svg | device-phone-mobile (outline) |
| printer.svg | printer (outline) |
| nas.svg | server-stack (outline) |
| speaker.svg | speaker-wave (outline) |
| game_console.svg | puzzle-piece (outline) |
| iot.svg | signal (outline) |

### Outline Icon Set

The outline icon set (`src/unifi_network_maps/assets/icons/outline/`) uses Lucide icons
for a technical wireframe style with consistent stroke weights.

#### Lucide Icons (ISC License)

Icon symbols from [Lucide](https://lucide.dev/).

- Source: https://github.com/lucide-icons/lucide
- License: ISC License (MIT-compatible)
- Style: Technical wireframe (uniform stroke-width: 2)

| Icon | Lucide Icon |
|------|-------------|
| gateway.svg | globe |
| switch.svg | hard-drive |
| ap.svg | radio |
| client.svg | monitor |
| other.svg | box |
| camera.svg | video |
| tv.svg | tv |
| phone.svg | smartphone |
| printer.svg | printer |
| nas.svg | server |
| speaker.svg | volume-2 |
| game_console.svg | gamepad-2 |
| iot.svg | wifi |

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
