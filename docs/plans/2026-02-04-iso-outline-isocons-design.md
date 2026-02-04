# Replace outline icon set with isocons.app (`iso-outline`)

## Overview

Replace the current `outline` icon set (Lucide, ISC license) with isometric icons from [isocons.app](https://www.isocons.app) (CC BY 4.0). Rename the set from `outline` to `iso-outline` to reflect the isometric style.

## Prerequisites (manual)

Download 13 SVG icons from isocons.app (website or [Figma plugin](https://www.figma.com/community/plugin/1413541312472258622/isocons)) and place them in `src/unifi_network_maps/assets/icons/iso-outline/`:

| File | Icon to find |
|------|-------------|
| `gateway.svg` | Router / gateway |
| `switch.svg` | Network switch |
| `ap.svg` | WiFi / access point |
| `camera.svg` | Camera / security cam |
| `tv.svg` | Monitor / TV |
| `phone.svg` | Smartphone / phone |
| `printer.svg` | Printer |
| `nas.svg` | Storage / server rack |
| `speaker.svg` | Speaker / audio |
| `game_console.svg` | Gamepad / controller |
| `iot.svg` | Sensor / chip / IoT |
| `client.svg` | Laptop / computer |
| `other.svg` | Generic device / cube |

Use the "Stroke" style from isocons for visual consistency.

## Implementation steps

### 1. Create icon directory

- [x] Prerequisites: SVGs downloaded and placed in `assets/icons/iso-outline/`
- [ ] Verify all 13 SVGs are present and valid
- [ ] Replace hardcoded fill/stroke colors with `#DECAL0` placeholder (if applicable, for theme color injection)

### 2. Rename icon set in code

- [ ] `src/unifi_network_maps/render/svg.py`: rename `outline` to `iso-outline` in `_ICON_SETS` registry
- [ ] `src/unifi_network_maps/render/svg.py`: update directory reference from `"outline"` to `"iso-outline"`
- [ ] `src/unifi_network_maps/cli/args.py`: update `--icon-set` choices from `outline` to `iso-outline`
- [ ] Remove old `assets/icons/outline/` directory (Lucide icons)

### 3. Update licenses

- [ ] `LICENSES.md`: replace Lucide (ISC) entry with isocons.app (CC BY 4.0) attribution
- [ ] Include link to license and credit to creators (Leye and Moses)

### 4. Update theme defaults

- [ ] Check if any theme YAML files reference `outline` as default icon set and update to `iso-outline`

### 5. Testing

- [ ] Unit tests: update icon set loading tests for `iso-outline`
- [ ] BDD tests: update any `--icon-set outline` scenarios to `--icon-set iso-outline`
- [ ] Regenerate smoketests: `make smoketest-mock`
- [ ] Update visual regression baselines: `make visual-baselines`
- [ ] Run full CI: `make ci`
