# TODO (Code Review Findings)

## P0 - Security
- no current (known) security concerns.

## P1 - Robustness
- no current (known) robustness concerns.

## P2 - Stability/UX
- no current (known) stability/UX concerns.

## P3 - Features
- Home Assistant integration (Lovelace cards + SVG/ports drilldown)
  - Approach choice: separate HA integration repo vs in-repo POC.
  - Pros (separate): independent release cadence, HA-specific UX freedom, easier HACS path.
  - Cons (separate): versioning boundary + compatibility overhead, more setup up front.
  - POC scope: render SVG + metadata JSON to `/config/www/unifi-network-maps/`.
  - UI ideas: isometric SVG card with pan/zoom + hover tooltips; device/port panel; PoE status badges.
  - Data model: stable JSON schema for devices/ports/links so UI can evolve without core changes.
  - Packaging options: pip in HA container, bundled wheel, or external renderer + file-based assets.
- Cable/link labeling
  - Feasibility: Medium; needs port metadata (`port_desc`, `port_overrides`) and consistent naming rules.
  - Plan: extend port label composition with optional cable-name mapping file; add tests for mixed labels.
- GUI tests for SVG outputs
  - Feasibility: Low/Medium; rendering comparison is brittle but doable with snapshot diffs.
  - Plan: add optional visual regression tests using generated SVGs + a baseline comparison step.
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

