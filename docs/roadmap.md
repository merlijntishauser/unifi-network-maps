# Roadmap

Items that belong to the `unifi-network-maps` CLI package. For adapter, model, and SVG render items, see `unifi-topology/docs/roadmap.md`.

## Moved to unifi-topology

The following sections moved to the `unifi-topology` library repo:

- Inline UniFi client (unifi_api.py) -- all items
- UniFi adapter (unifi.py) -- all items
- Model layer -- all items
- Render layer: SVG-related items (orthogonal/isometric duplication, svg_layout.py, svg_edges.py tests)

## Render layer (CLI-only)

### Render module test coverage
Remaining CLI render modules with no dedicated unit tests:
- `legend.py` - legend element construction
- `mermaid_theme.py` - theme variable application

## CLI layer

### Split long orchestration functions
Several CLI functions exceed the 15-line guideline significantly:
- `render.py`: `render_svg_output` (69 lines), `render_standard_format` (63 lines), `render_mkdocs_format` (52 lines) -- each mixes multiple concerns (layout, groups, clients, WAN, theme)
- `main.py`: `main` (66 lines), `_handle_json_format` (30 lines) -- duplicated payload construction for mock vs real data
- `runtime.py`: `build_edges_with_clients` (33 lines) -- two code paths for client loading with duplicated index logic

Lower priority than model/render items since CLI orchestration functions naturally tend longer and the complexity is sequential rather than cyclomatic.

### Tighten CLI type annotations
`list[object]` appears as return/parameter type in `main.py` and `runtime.py` where `list[dict[str, object]]` or more specific types would be appropriate. `args.py` uses the private `argparse._ArgumentGroup` type.

### Extract shared client-loading logic in runtime.py
Client fetching pattern (fetch clients, build device index, build client edges) appears 3 times across `build_edges_with_clients` and `resolve_mkdocs_client_ports`. A shared `_load_clients()` helper would eliminate the duplication.

## Test suite

### Consolidate test fixture duplication
Several device factory helpers are duplicated across test files:
- `_make_minimal_device()` -- identical in `test_cli_render.py` and `test_runtime.py`
- `_make_args()` -- identical in `test_cli_render.py` and `test_runtime.py`
- Device factory variants with different signatures in `test_device_summary.py`, `test_mkdocs.py`, `test_topology.py`

Consolidate into `conftest.py` or a shared `tests/factories.py`.

### Fix pytest marker consistency
Only 8 of 41 test files have explicit markers; the rest rely on auto-marking in `conftest.py` which defaults to `unit`. Multi-module tests like `test_topology.py` should be explicitly marked `integration`.
