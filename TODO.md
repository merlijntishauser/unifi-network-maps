# TODO (Refactor Proposals)

## P0 - Correctness/Clarity
- (done)

## P1 - Maintainability
- (done)

## P2 - Cleanup/Quality
- **Drop generated `*.egg-info` from `src/`:** Ensure they are not tracked and update `.gitignore` if needed.
- **Config loading ergonomics:** Move `load_dotenv()` into CLI so `Config.from_env()` doesn’t hard-depend on `python-dotenv` for library usage.
- **Stronger tests around PoE detection:** Add focused tests for `poe_power`/`poe_good` and for missing port tables.
