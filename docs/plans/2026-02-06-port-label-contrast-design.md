# Port Label Contrast Fix

Addresses: https://github.com/merlijntishauser/unifi-network-maps/issues/32

## Problem

Port labels on edges have poor contrast on dark themes:

1. **Isometric SVG**: Port label text color is hardcoded to `fill="#555"` in `_render_iso_port_label()` (svg_isometric.py:701), ignoring the theme entirely.
2. **Orthogonal SVG**: Port labels inside node boxes use `theme.text_secondary`, which has reasonable contrast against the SVG background but sits on top of node tile gradient fills, reducing readability.

Both issues are worst on dark themes but slightly visible on light themes too.

## Solution

Use a consistent `paint-order: stroke fill` text halo on port labels in both renderers. This adds a contrasting outline behind the text that ensures readability against any background.

### Changes

#### 1. `svg_isometric.py` — `_render_iso_port_label()`

- Add `theme: SvgTheme` parameter.
- Replace hardcoded `fill="#555"` with `fill="{theme.text_secondary}"`.
- Add `stroke="{theme.background}" stroke-width="3" paint-order="stroke fill"` to the `_render_iso_text()` call.
- Thread `theme` through from `_render_iso_node()` call site.

#### 2. `svg_isometric.py` — `_render_iso_text()`

- Add optional `stroke` and `stroke_width` parameters.
- When provided, add `stroke`, `stroke-width`, and `paint-order="stroke fill"` attributes to the `<text>` element.

#### 3. `svg.py` — `_render_svg_nodes()`

- Add `stroke="{theme.background}" stroke-width="3" paint-order="stroke fill"` to the port label `<text>` element (line 849-856).

#### 4. Theme files

No changes needed. Existing `text_secondary` values are appropriate. The halo effect handles contrast against varying node fills.

## Files Modified

- `src/unifi_network_maps/render/svg.py`
- `src/unifi_network_maps/render/svg_isometric.py`
