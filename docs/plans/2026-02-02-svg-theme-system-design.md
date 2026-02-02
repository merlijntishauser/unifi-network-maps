# SVG Theme System with UniFi-aligned Colors

**Issue:** #22
**Date:** 2026-02-02
**Status:** Approved

## Summary

Extend the existing SVG theme system with built-in theme names, additional color properties (background, text, status, WAN globe), and UniFi-inspired color palettes.

## Design Decisions

1. **Color approach:** UniFi-inspired but distinct colors for device types (not monochromatic)
2. **CLI interface:** Separate `--theme` flag for built-in themes alongside existing `--theme-file`
3. **Schema extension:** Add background, text (primary/secondary), status (online/offline), and WAN globe colors
4. **Built-in themes:** unifi, unifi-dark, minimal, classic, classic-dark

## Theme Schema Extension

### SvgTheme Dataclass

```python
@dataclass(frozen=True)
class SvgTheme:
    # Links
    link_standard: tuple[str, str]
    link_poe: tuple[str, str]

    # Nodes
    node_gateway: tuple[str, str]
    node_switch: tuple[str, str]
    node_ap: tuple[str, str]
    node_client: tuple[str, str]
    node_other: tuple[str, str]
    node_client_cluster: tuple[str, str] = ("#d4b8ff", "#a080e0")

    # Groups
    group_fill: str = "#f8f9fa"
    group_stroke: str = "#dee2e6"
    group_radius: int = 8
    group_label_fill: str = "#495057"
    group_stroke_width: int = 2

    # VLANs
    vlan_colors: dict[int, str] = field(default_factory=dict)

    # New: Background & text
    background: str = "#ffffff"
    text_primary: str = "#1a1a1a"
    text_secondary: str = "#6b7280"

    # New: Status indicators
    status_online: str = "#00a86b"
    status_offline: str = "#ef4444"

    # New: WAN globe
    wan_globe: tuple[str, str] = ("#4fc3f7", "#0288d1")
```

### YAML Schema

```yaml
svg:
  background: "#ffffff"
  text:
    primary: "#1a1a1a"
    secondary: "#6b7280"
  status:
    online: "#00a86b"
    offline: "#ef4444"
  wan_globe:
    from: "#4fc3f7"
    to: "#0288d1"
  links:
    standard: { from: "...", to: "..." }
    poe: { from: "...", to: "..." }
  nodes:
    gateway: { from: "...", to: "..." }
    # ... etc
```

## CLI Interface

### New Argument

```python
parser.add_argument(
    "--theme",
    choices=["unifi", "unifi-dark", "minimal", "classic", "classic-dark"],
    default=None,
    help="Built-in theme name",
)
```

### Precedence Rules

1. `--theme-file` takes priority if both specified
2. `--theme` selects a built-in theme
3. Neither specified → uses classic (current default behavior)

### Resolution Logic

```python
BUILTIN_THEMES = {
    "unifi": "unifi.yaml",
    "unifi-dark": "unifi-dark.yaml",
    "minimal": "minimal.yaml",
    "classic": "default.yaml",
    "classic-dark": "dark.yaml",
}

def resolve_themes(
    theme_name: str | None = None,
    theme_file: str | Path | None = None,
) -> tuple[MermaidTheme, SvgTheme]:
    if theme_file:
        return load_theme(theme_file)
    if theme_name:
        builtin_path = ASSETS_DIR / "themes" / BUILTIN_THEMES[theme_name]
        return load_theme(builtin_path)
    return DEFAULT_MERMAID_THEME, DEFAULT_SVG_THEME
```

## Built-in Theme Palettes

### unifi.yaml (light)

```yaml
svg:
  background: "#ffffff"
  text:
    primary: "#1a1a1a"
    secondary: "#6b7280"
  status:
    online: "#00a86b"
    offline: "#ef4444"
  wan_globe:
    from: "#4fc3f7"
    to: "#0288d1"
  links:
    standard: { from: "#006fff", to: "#0052cc" }
    poe: { from: "#00a86b", to: "#007a4d" }
  nodes:
    gateway: { from: "#006fff", to: "#0052cc" }
    switch: { from: "#00a86b", to: "#007a4d" }
    ap: { from: "#6366f1", to: "#4f46e5" }
    client: { from: "#94a3b8", to: "#64748b" }
    other: { from: "#cbd5e1", to: "#94a3b8" }
```

### unifi-dark.yaml

```yaml
svg:
  background: "#111827"
  text:
    primary: "#f9fafb"
    secondary: "#9ca3af"
  status:
    online: "#34d399"
    offline: "#f87171"
  wan_globe:
    from: "#38bdf8"
    to: "#0284c7"
  links:
    standard: { from: "#3b82f6", to: "#2563eb" }
    poe: { from: "#34d399", to: "#10b981" }
  nodes:
    gateway: { from: "#1e3a5f", to: "#0f2744" }
    switch: { from: "#14532d", to: "#0a3621" }
    ap: { from: "#312e81", to: "#1e1b4b" }
    client: { from: "#334155", to: "#1e293b" }
    other: { from: "#374151", to: "#1f2937" }
```

### minimal.yaml

```yaml
svg:
  background: "#fafafa"
  text:
    primary: "#374151"
    secondary: "#9ca3af"
  status:
    online: "#6b7280"
    offline: "#9ca3af"
  wan_globe:
    from: "#d1d5db"
    to: "#9ca3af"
  nodes:
    gateway: { from: "#e5e7eb", to: "#d1d5db" }
    switch: { from: "#e5e7eb", to: "#d1d5db" }
    ap: { from: "#e5e7eb", to: "#d1d5db" }
    client: { from: "#f3f4f6", to: "#e5e7eb" }
    other: { from: "#f3f4f6", to: "#e5e7eb" }
  links:
    standard: { from: "#9ca3af", to: "#6b7280" }
    poe: { from: "#6b7280", to: "#4b5563" }
```

## Implementation Plan

### Files to Modify

| File | Changes |
|------|---------|
| `cli/args.py` | Add `--theme` argument with choices |
| `cli/render.py` | Pass theme_name to resolve_themes |
| `render/svg_theme.py` | Add new fields to SvgTheme dataclass |
| `render/theme.py` | Add BUILTIN_THEMES dict, update resolve_themes() signature |
| `render/svg.py` | Use theme.background, theme.text_*, theme.wan_globe |

### Files to Create

| File | Content |
|------|---------|
| `assets/themes/unifi.yaml` | UniFi light palette |
| `assets/themes/unifi-dark.yaml` | UniFi dark palette |
| `assets/themes/minimal.yaml` | Minimal palette |

### Existing Files (unchanged)

- `assets/themes/default.yaml` → aliased as `classic`
- `assets/themes/dark.yaml` → aliased as `classic-dark`

### Tests to Add

- Test `--theme` flag parsing
- Test theme resolution precedence (--theme-file wins over --theme)
- Test new theme fields load correctly from YAML
- Test default values for new fields when not specified in YAML
