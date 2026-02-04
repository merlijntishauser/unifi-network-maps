# Per-Type Icon Decal Colors

## Goal

Make modern icon decals on isometric nodes match the node's top surface color (darker variant), instead of using a single flat `icon_decal` color for all device types.

## Design

### Color derivation

Each node type has a gradient tuple `(from, to)` in the theme. The "to" value is the darker end of the top surface gradient. The icon decal color is computed by darkening that value by 35%.

Example for UniFi theme gateway (`#006fff` → darkened → `#0048b3`):
the icon symbol on a gateway node will be a deep blue that reads as "etched into" the blue surface.

### Code changes

**`svg.py`** only — no theme schema or YAML changes.

1. `_darken_hex(color: str, factor: float = 0.35) -> str`
   - Parses 6-digit hex to RGB, multiplies each channel by `(1 - factor)`, returns hex.

2. `_build_decal_colors(theme: SvgTheme, factor: float = 0.35) -> dict[str, str]`
   - Reads `node_gateway`, `node_switch`, `node_ap`, `node_client`, `node_other`, `node_camera`, `node_tv`, `node_phone`, `node_printer`, `node_nas`, `node_speaker`, `node_game_console`, `node_iot` from the theme.
   - Takes the second element (darker gradient end) of each tuple and darkens it.
   - Returns `{"gateway": "#...", "switch": "#...", ...}`.

3. Modify `_load_isometric_icons(icon_set, decal_color, ...)` call site in the isometric renderer:
   - Before calling, build the per-type color map.
   - Change `_load_isometric_icons()` to accept `decal_colors: dict[str, str]` and a `fallback_decal: str`.
   - When replacing `#DECAL0`, use `decal_colors.get(device_type, fallback_decal)`.

### Backwards compatibility

- `icon_decal` theme field unchanged; serves as fallback for unmapped types and orthogonal rendering.
- Isometric icon set icons don't use `#DECAL0` so are unaffected.
- Only the modern icon set on isometric output is affected.

### Emboss filter

No changes. The existing `icon-emboss` filter with highlight/shadow edges complements the darker color-matched decals.
