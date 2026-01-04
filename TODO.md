# TODO (Refactor Proposals)

## P0 - Correctness/Clarity
- Done

## P1 - Maintainability
- Split `main()` in `cli.py` into parse/config/build/render steps to reduce branching complexity.
- Extract SVG layout constants (tile sizes, spacing, angles) into a single config dataclass for reuse.
- Consolidate theme handling into a single loader + default injector to avoid repeated `load_theme` calls.

## P2 - Cleanup/Quality
- done
- Move shared regex helpers (port parsing) into `labels.py` or `ports.py`.
- Add explicit type aliases for `PortMap`/`PoeMap` to improve readability.
- Reduce long functions (>15 lines) by extracting label/positioning logic into helpers.
