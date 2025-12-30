# TODO (Refactor Proposals)

## P0 - Correctness/Clarity
- **Define a typed device adapter:** Introduce a lightweight Protocol/dataclass for the UniFi device fields we use (name/mac/type/lldp/port_table) to make expectations explicit and reduce defensive `getattr` usage.

## P1 - Maintainability
- **Extract debug dump into its own module:** Move `_debug_dump_devices` and `_device_to_dict` into `debug.py` and keep CLI thin.
- **Centralize LLDP/port parsing:** Consolidate LLDP parsing and port label logic into a dedicated helper class or module to keep `topology.py` smaller.
- **Replace BFS list queue with `deque`:** Use `collections.deque` in `build_tree_edges_by_topology` for clarity and efficiency.
- **Unify label composition:** Provide a single utility for edge label rendering (ports, PoE) to avoid drifting logic between topology and mermaid.

## P2 - Cleanup/Quality
- **Drop generated `*.egg-info` from `src/`:** Ensure they are not tracked and update `.gitignore` if needed.
- **Config loading ergonomics:** Move `load_dotenv()` into CLI so `Config.from_env()` doesn’t hard-depend on `python-dotenv` for library usage.
- **Stronger tests around PoE detection:** Add focused tests for `poe_power`/`poe_good` and for missing port tables.
