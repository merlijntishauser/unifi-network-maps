# Custom Fonts in SVG Themes

## Goal

Allow themes to specify a custom font that gets base64-embedded into SVG output, producing self-contained files that render identically everywhere. The UniFi themes use Inter (matching ui.com), the minimal theme uses Space Grotesk, and classic themes keep system fonts.

## Font assignments

| Theme | Font | Rationale |
|-------|------|-----------|
| `unifi` | Inter | Closest free match to UI Sans (ui.com typeface) |
| `unifi-dark` | Inter | Same brand consistency |
| `minimal` | Space Grotesk | Technical, monospace-inspired feel fits the understated style |
| `classic` | (system) | Arial/Helvetica — no custom font, matches "classic" identity |
| `classic-dark` | (system) | Same as classic |

## Font files

Two weights per font: regular (400) for secondary text, semibold (600) for device name labels.

```
src/unifi_network_maps/assets/fonts/
├── inter-regular.woff2          (~95 KB)
├── inter-semibold.woff2         (~95 KB)
├── INTER_LICENSE                 (SIL Open Font License 1.1)
├── space-grotesk-regular.woff2  (~50 KB)
├── space-grotesk-semibold.woff2 (~50 KB)
└── SPACE_GROTESK_LICENSE         (SIL Open Font License 1.1)
```

Source URLs:
- Inter: https://github.com/rsms/inter (SIL OFL 1.1)
- Space Grotesk: https://github.com/nicxn/spacegrotesk (SIL OFL 1.1, also on Google Fonts)

## Theme property

Add `font_family: str | None = None` to `SvgTheme`. When `None`, SVGs use the current system font stack (`Arial,Helvetica,sans-serif`). When set (e.g., `"Inter"`), the renderer:

1. Resolves WOFF2 files by convention: `{name_lower}-regular.woff2`, `{name_lower}-semibold.woff2`
2. Base64-encodes and injects `@font-face` declarations into the SVG `<style>` block
3. Prepends the font name to the CSS font-family stack: `Inter,Arial,Helvetica,sans-serif`

If only the regular file exists, the semibold is skipped gracefully.

## SVG output

The generated `<style>` block becomes:

```html
<style>
@font-face { font-family: 'Inter'; font-weight: 400;
  src: url(data:font/woff2;base64,...) format('woff2'); }
@font-face { font-family: 'Inter'; font-weight: 600;
  src: url(data:font/woff2;base64,...) format('woff2'); }
text { font-family: Inter,Arial,Helvetica,sans-serif; }
text.node-label { font-weight: 600; }
</style>
```

Device name labels get `class="node-label"` and render in semibold (600). All other text (ports, IPs, secondary labels) stays regular (400).

## Files to modify

| File | Change |
|------|--------|
| `svg_theme.py` | Add `font_family: str \| None = None` field |
| `theme.py` | Wire `font_family` from YAML (`None` if absent) |
| `svg.py` | Font loading helper, inject `@font-face`, update CSS in both renderers, add `node-label` class to device names |
| `unifi.yaml` | Add `font_family: "Inter"` |
| `unifi-dark.yaml` | Add `font_family: "Inter"` |
| `minimal.yaml` | Add `font_family: "Space Grotesk"` |
| `LICENSES.md` | Add Inter and Space Grotesk sections |
| `assets/fonts/` | New directory with WOFF2 files and license files |

## Package size impact

- Inter: ~190 KB (two weights)
- Space Grotesk: ~100 KB (two weights)
- Total: ~290 KB added to the package
- Only embedded into SVGs that use the font — other themes pay zero cost
