# TODO (Code Review Findings)

## P0 - Security
- no current (known) security concerns.

## P1 - Robustness
- no current (known) robustness concerns.

## P2 - Stability/UX
- no current stability/UX concerns.

## P3 - Features
- Home Assistant export/integration
  - Feasibility: Medium; export layer already exists, needs HA-specific examples.
  - Plan: add HA export presets (markdown card + include), document `/config/www` flow, keep core logic unchanged.
- Cable/link labeling
  - Feasibility: Medium; needs port metadata (`port_desc`, `port_overrides`) and consistent naming rules.
  - Plan: extend port label composition with optional cable-name mapping file; add tests for mixed labels.
- GUI tests for SVG outputs
  - Feasibility: Low/Medium; rendering comparison is brittle but doable with snapshot diffs.
  - Plan: add optional visual regression tests using generated SVGs + a baseline comparison step.
- QR codes
  - Feasibility: Low; requires external QR library and decisions on what to encode (device URL/IP/name).
  - Plan: add optional `--include-qr` with opt-in dependency; render QR nodes or sidecar assets.
- Web interface?
