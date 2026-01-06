# TODO (Refactor Proposals)

## P0 - Correctness/Clarity
- Done

## P1 - Maintainability
- Done

## P2 - Cleanup/Quality
- done

## P3 - Features
- Home Assistant export/integration
  - Feasibility: Medium; export layer already exists, needs HA-specific examples.
  - Plan: add HA export presets (markdown card + include), document /config/www flow, keep core logic unchanged.
- Export LLDP as markdown (all info per device)
  - Feasibility: High; data already available after normalization.
  - Plan: add `--format lldp-md` or `--export lldp` to dump per-device LLDP tables into Markdown.
- Cable/link labeling
  - Feasibility: Medium; needs port metadata (`port_desc`, `port_overrides`) and consistent naming rules.
  - Plan: extend port label composition with optional cable-name mapping file; add tests for mixed labels.
- Material for MkDocs integration
  - Feasibility: Low/Medium; requires theme-specific markdown conventions and Mermaid rendering notes.
  - Plan: add example `mkdocs.yml` snippet, sample page, and guidance for Mermaid plugin setup.
- Static code analysis
  - Feasibility: High; add mypy/pyright and stricter ruff rules incrementally.
  - Plan: introduce a `typecheck` make target and CI job; start with module-by-module typing.
- BDD scenarios (Behave)
  - Feasibility: Medium; adds an extra test framework but can target CLI smoke flows.
  - Plan: define feature files for common CLI paths (mermaid/svg/iso), add fixtures for cached API responses.
- GUI tests for SVG outputs
  - Feasibility: Low/Medium; rendering comparison is brittle but doable with snapshot diffs.
  - Plan: add optional visual regression tests using generated SVGs + a baseline comparison step.
- QR codes
  - Feasibility: Low; requires external QR library and decisions on what to encode (device URL/IP/name).
  - Plan: add optional `--include-qr` with opt-in dependency; render QR nodes or sidecar assets.

- contract test with unifi api, make sure the api call results match our expectations
- webinterface?!