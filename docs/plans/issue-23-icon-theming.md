# Issue #23: Enhanced Isometric Icons with Theming

## Status

| Phase | Status | Commit |
|-------|--------|--------|
| Phase 1: Infrastructure + Modern Icons | ✅ Complete | `6c37063` |
| Phase 2: Flat/Minimal Icon Set | ✅ Complete | - |
| Phase 3: Outline/Wireframe Icon Set | ✅ Complete | - |
| Phase 4: Extended Device Types | Pending | - |

## Overview

Upgrade the icon system to support multiple selectable icon sets with improved visual design. This enables users to choose icon styles that match their documentation needs.

## Design Decisions

| Aspect | Decision |
|--------|----------|
| **Selection mechanism** | `--theme` sets default icon set, `--icon-set` can override |
| **Icon sets planned** | `legacy` (current) → `modern` → `flat` → `outline` |
| **First new style** | Modern isometric (base shapes + Heroicons) |
| **Core device types** | Gateway, Switch, AP, Client, Other |
| **Icon sourcing** | Isometric base shapes + Heroicons (MIT) with matrix transform |
| **License compliance** | LICENSES.md + README attribution |

## Theme-to-Icon-Set Defaults

| Theme | Default Icon Set |
|-------|------------------|
| `unifi` | `modern` |
| `unifi-dark` | `modern` |
| `minimal` | `modern` (will be `flat` when available) |
| `classic` | `legacy` |
| `classic-dark` | `legacy` |

---

## Phase 1: Infrastructure + Modern Isometric Set ✅

*Completed: 2026-02-02*

### 1.1 CLI Changes

- [x] Add `--icon-set` argument with choices: `legacy`, `modern`
- [x] CLI override takes precedence over theme default

### 1.2 Theme Schema Extension

- [x] Add `icon_set` field to theme YAML schema
- [x] Update `SvgTheme` dataclass with `icon_set: str` field
- [x] Modify theme loading to respect icon_set from theme or CLI override
- [x] Update built-in theme YAML files with icon_set defaults

### 1.3 Icon Loading Refactor

- [x] Refactor `_load_isometric_icons()` to accept icon_set parameter
- [x] Refactor `_load_icons()` to accept icon_set parameter
- [x] Create icon set registry mapping set names to directory paths
- [x] Fallback logic: if icon missing in set, fall back to `legacy`

### 1.4 Asset Structure

- [x] Create `assets/icons/modern/` directory for isometric icons
- [x] Create 5 modern icons: gateway, switch, ap, client, other
- [x] Custom icons matching isopacks 30° isometric style and color palette

### 1.5 Attribution

- [x] Update `LICENSES.md` with icon sources
- [x] Add credits reference to README.md

### 1.6 Testing

- [x] Add unit tests for icon set loading with fallback
- [x] Add BDD scenarios for `--icon-set` flag
- [x] Update smoketest-mock with icon set variants
- [x] Update visual regression baselines

---

## Phase 2: Flat/Minimal Icon Set ✅

*Completed: 2026-02-03*

### 2.1 Icon Sourcing

- [x] Source flat/minimal style icons for: gateway, switch, ap, client, other
- [x] Ensure 2D style works well at small sizes (Heroicons outline)
- [x] Verify license compatibility (MIT)
- [x] Add to `LICENSES.md`

### 2.2 Implementation

- [x] Populate `assets/icons/flat/` directory
- [x] Add `flat` to `--icon-set` choices
- [x] Update `minimal` theme to default to `flat` icon set
- [x] Smoketest includes flat icon rendering via minimal theme

### 2.3 Testing

- [x] Unit tests for flat icon loading
- [x] Smoketest validates flat icon rendering

---

## Phase 3: Outline/Wireframe Icon Set ✅

*Completed: 2026-02-03*

### 3.1 Icon Sourcing

- [x] Source outline/wireframe style icons for: gateway, switch, ap, client, other
- [x] Ensure line-art style has consistent stroke weight (Lucide: stroke-width 2)
- [x] Verify license compatibility (ISC - MIT-compatible)
- [x] Add to `LICENSES.md`

### 3.2 Implementation

- [x] Create `assets/icons/outline/` directory
- [x] Populate with Lucide icons
- [x] Add `outline` to `--icon-set` choices

### 3.3 Testing

- [x] Unit tests for outline icon loading
- [x] Smoketest validates outline icon rendering via --icon-set flag

---

## Phase 4: Extended Device Types

*Depends on: Phase 1 complete (can run parallel to Phase 2/3)*

### 4.1 Device Type Detection

- [ ] Map UniFi fingerprints to device categories
- [ ] OUI-based manufacturer detection for common devices
- [ ] Name heuristics (contains "TV", "Sonos", "Printer", etc.)
- [ ] Add `device_category` field to client data model

### 4.2 Additional Icons (per set that exists)

Priority device types to add:
- [ ] `camera` - UniFi Protect / security cameras
- [ ] `tv` - Smart TVs, streaming devices
- [ ] `phone` - Mobile devices, VoIP phones
- [ ] `printer` - Network printers
- [ ] `nas` - Network storage
- [ ] `speaker` - Smart speakers (Sonos, HomePod)
- [ ] `game_console` - Gaming devices
- [ ] `iot` - Generic IoT/smart home devices
- [ ] `unknown` - Fallback for unidentified devices

### 4.3 Icon Variants

- [ ] Status variants: online (normal), offline (dimmed/grayed)
- [ ] Consider size variants for dense layouts

---

## Current File Structure

```
src/unifi_network_maps/assets/icons/
├── (root flat icons)        # Legacy flat icons
│   ├── router-network.svg
│   ├── server-network.svg
│   ├── access-point.svg
│   └── laptop.svg
├── isometric/               # Legacy isometric icons (isopacks)
│   ├── router.svg
│   ├── switch-module.svg
│   ├── tower.svg
│   ├── laptop.svg
│   └── server.svg
└── modern/                  # Phase 1: Minimalistic icons
    ├── gateway.svg
    ├── switch.svg
    ├── ap.svg
    ├── client.svg
    └── other.svg
```

---

## Icon Sourcing Guidelines

### License Requirements
- Must be compatible with MIT license
- Acceptable: MIT, Apache 2.0, CC0, CC-BY, BSD
- Requires attribution: CC-BY (document in LICENSES.md)
- Not acceptable: CC-NC (non-commercial), GPL (copyleft)

### Visual Consistency Checklist
- [ ] Same lighting direction (top-left light source for isometric)
- [ ] Consistent color palette or easily recolorable
- [ ] Similar level of detail/complexity
- [ ] Matching perspective angle for isometric sets
- [ ] Consistent stroke weight for outline sets

### Recommended Sources
- [FreeSVG](https://freesvg.org/) - Public domain
- [Vecteezy](https://www.vecteezy.com/) - Check individual licenses
- [SVG Repo](https://www.svgrepo.com/) - Various open licenses
- [Lucide](https://lucide.dev/) - MIT license, outline style
- [Tabler Icons](https://tabler-icons.io/) - MIT license
