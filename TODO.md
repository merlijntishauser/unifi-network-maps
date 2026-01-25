# TODO (Code Review Findings)

## P0 - Security
- 
- **Race Condition in Cache File Operations** (HIGH)
  - File: `src/unifi_network_maps/adapters/unifi.py:272-275`
  - Window between `tmp_path.write_text()` and `tmp_path.replace()` allows file modification
  - Fix: Use `os.O_EXCL`, set restrictive permissions immediately on temp file
- **Incomplete XSS Protection in SVG Output** (MEDIUM)
  - File: `src/unifi_network_maps/render/svg.py:106`
  - Custom `_escape_text()` only escapes `&<>`; should use `html.escape()` for consistency
- **Potential Exception Leak of Sensitive Information** (MEDIUM)
  - Files: `src/unifi_network_maps/cli/main.py:72,90,95`, `src/unifi_network_maps/cli/runtime.py:126,136`
  - Broad exception handlers log exception details; may leak credentials/tokens
  - Fix: Sanitize exception messages before logging
- **Insecure Temporary File Creation** (MEDIUM)
  - File: `src/unifi_network_maps/io/export.py:20-31`
  - `NamedTemporaryFile(delete=False)` may not cleanup on error; predictable naming
  - Fix: Use `os.O_EXCL`, ensure cleanup in finally block

## P1 - Robustness
- **Denial of Service via Unbounded Mock Generation** (HIGH)
  - File: `src/unifi_network_maps/cli/main.py:54-60`
  - `--mock-switches/aps/clients` accept arbitrary integers; `--mock-switches=999999999` causes memory exhaustion
  - Fix: Add reasonable upper limits (e.g., max 10000 devices per type)
- **Missing Size Validation for SVG Dimensions** (MEDIUM)
  - File: `src/unifi_network_maps/cli/args.py:119-120`
  - `--svg-width/height` accept any integer; negative or extremely large values cause issues
  - Fix: Validate range (e.g., 100-50000)
- **Insufficient Input Validation on Legend Scale** (MEDIUM)
  - File: `src/unifi_network_maps/cli/args.py:101`
  - `--legend-scale` accepts any float; negative or large values cause rendering issues
  - Fix: Validate range (e.g., 0.1-10.0)
- **No Maximum File Size Check** (LOW)
  - Multiple files reading user-supplied files
  - Very large mock data or theme files cause memory exhaustion
  - Fix: Check file size before reading (e.g., max 10MB)
- **Unvalidated Environment Variable Integers** (LOW)
  - File: `src/unifi_network_maps/adapters/unifi.py:219-225,281-287,291-298,302-309`
  - Env vars (`UNIFI_CACHE_TTL_SECONDS`, `UNIFI_RETRY_ATTEMPTS`, etc.) use `.isdigit()` but no range validation
  - Fix: Add reasonable bounds checks after conversion
- **Missing Validation on Timezone String** (LOW)
  - File: `src/unifi_network_maps/cli/args.py:150`
  - `--mkdocs-timestamp-zone` accepts arbitrary strings; invalid timezones cause runtime errors
  - Fix: Validate against known timezone database

## P2 - Stability/UX
- no current (known) stability/UX concerns.

## P3 - Features
- Unifi 2D theme, matching Ubiquiti's 2D theme.
- Clients not only placed horizontally on one row, but multiple rows to keep SVG more square
- Cable/link labeling
  - Feasibility: Medium; needs port metadata (`port_desc`, `port_overrides`) and consistent naming rules.
  - Plan: extend port label composition with optional cable-name mapping file; add tests for mixed labels.
- GUI tests for SVG outputs
  - Feasibility: Low/Medium; rendering comparison is brittle but doable with snapshot diffs.
  - Plan: add optional visual regression tests using generated SVGs + a baseline comparison step.
  - Note: include a vertical-link snapshot to catch zero-width path regressions.
- QR codes for devices
  - Feasibility: Low; requires external QR library and decisions on what to encode (device URL/IP/name).
  - Plan: add optional `--include-qr` with opt-in dependency; render QR nodes or sidecar assets.
- Web interface (POC Option A with path to Option B)
  - Feasibility: Medium; local-only FastAPI + static UI that wraps existing render pipeline.
  - Pros: quick POC, no CLI breaking changes, easy preview/export, minimal ops/security risk.
  - Cons: extra dependencies, UI/CLI drift risk, packaging story for future embedded `--web`.
  - Scope: choose data source (mock with sliders + generate, or real UniFi controller selection).
  - Option B details: embed server behind `--web` flag, run in-process using shared render functions.
    - Pros: “one binary/one package”; great UX.
    - Packaging: keep UI assets under `assets/web/`, serve via FastAPI/Starlette `StaticFiles`.
    - UX: same form as Option A, but ships with package and requires no external setup.
    - Safety: explicit local bind (127.0.0.1), optional `--web-host/--web-port`, no creds stored.
    - Extensibility: add controller profiles in config file later without changing UI routes.
