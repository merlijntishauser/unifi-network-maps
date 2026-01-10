# TODO (Code Review Findings)

## P0 - Security
- no current security concerns.

## P1 - Robustness
- Add timeouts for UniFi API calls (if supported by `unifi-controller-api`) or implement a wrapper timeout.
  - Risk: calls can hang indefinitely, blocking CLI.
  - Plan: expose `UNIFI_REQUEST_TIMEOUT_SECONDS` and pass into controller init if supported.
- Harden Mermaid label escaping for newlines/backslashes.
  - Risk: device names/port labels with control characters can break Mermaid output.
  - Plan: escape `\n`, `\r`, `\\` in `_escape` and normalize whitespace.

## P2 - Stability/UX
- Make output writes atomic when `--output` is set.
  - Risk: interrupted runs can leave partial files.
  - Plan: write to temp file in same dir and replace on success.

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
