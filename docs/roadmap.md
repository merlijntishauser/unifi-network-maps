# Roadmap

Items that belong to the `unifi-network-maps` CLI package.
For adapter, model, and SVG render items, see the [unifi-topology roadmap](https://github.com/merlijntishauser/unifi-topology).

## Security

- **Broad exception handlers in runtime.py** (MEDIUM)
  - `runtime.py` has `except Exception` handlers (lines ~54, ~107, ~179) that log full exception messages at debug/warning/error level; could leak credentials or tokens
  - Fix: Narrow to specific exception types or sanitize messages before logging

## Robustness

- **Unbounded mock generation** (HIGH)
  - `cli/main.py`: `--mock-switches/aps/clients` accept arbitrary integers with no upper bound; extreme values cause memory exhaustion
  - Fix: Add reasonable upper limits (e.g., max 10000 per type)
- **Missing SVG dimension validation** (MEDIUM)
  - `cli/args.py`: `--svg-width/height` accept any integer including negative or extreme values
  - Fix: Validate range (e.g., 100-50000)
- **Missing legend scale validation** (MEDIUM)
  - `cli/args.py`: `--legend-scale` accepts any float including negative
  - Fix: Validate range (e.g., 0.1-10.0)
- **Missing file size check** (LOW)
  - Multiple files read user-supplied mock data and theme files with no size limit
  - Fix: Check file size before reading (e.g., max 10MB)
- **Missing timezone validation** (LOW)
  - `cli/args.py`: `--mkdocs-timestamp-zone` accepts arbitrary strings; invalid timezones fail at runtime
  - Fix: Validate against known timezone database

## Code quality

### Long orchestration functions
Several CLI functions exceed the 15-line guideline:
- `render.py`: `render_svg_output` (~70 lines), `render_standard_format` (~63 lines), `render_mkdocs_format` (~53 lines)
- `main.py`: `main` (~67 lines), `_handle_json_format` (~31 lines)
- `runtime.py`: `build_edges_with_clients` (~34 lines)

Lower priority since CLI orchestration naturally tends longer and the complexity is sequential rather than cyclomatic.

### Tighten CLI type annotations
`list[object]` appears as return/parameter type in `main.py` and `runtime.py` where `list[dict[str, object]]` or more specific types would be appropriate. `args.py` uses the private `argparse._ArgumentGroup` type.

### Extract shared client-loading logic in runtime.py
Client fetching pattern (fetch clients, build device index, build client edges) appears 3 times across `build_edges_with_clients` and `resolve_mkdocs_client_ports`. A shared helper would eliminate the duplication.

## Test suite

### Missing dedicated tests
- `mermaid_theme.py` lacks a dedicated test file (only indirect coverage via `test_mermaid.py`)

### Consolidate test fixture duplication
Several device factory helpers are duplicated across test files:
- `_make_minimal_device()` -- identical in `test_cli_render.py` and `test_runtime.py`
- `_make_args()` -- identical in `test_cli_render.py` and `test_runtime.py`

Consolidate into `conftest.py` or a shared `tests/factories.py`.

### Fix pytest marker consistency
Only 4 of 16 test files have explicit markers; the rest rely on auto-marking in `conftest.py` which defaults to `unit`. Multi-module tests should be explicitly marked `integration`.

## Features

- **QR codes for devices**
  - Requires external QR library and decisions on what to encode (device URL/IP/name)
  - Plan: add optional `--include-qr` with opt-in dependency; render QR nodes or sidecar assets
- **Web interface**
  - Local-only FastAPI + static UI wrapping the existing render pipeline
  - Option A: standalone dev server; Option B: embed behind `--web` flag
  - Safety: explicit local bind (127.0.0.1), optional `--web-host/--web-port`, no creds stored
