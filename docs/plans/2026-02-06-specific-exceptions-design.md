# Improve: Use specific exception types instead of broad Exception catches

Addresses [#30](https://github.com/merlijntishauser/unifi-network-maps/issues/30).

## Problem

Several places catch broad `Exception` where the set of expected exceptions is
well-defined. This reduces debuggability and silently swallows unexpected errors.

## Scope

Only the clear-cut cases where specific types are known. Intentionally broad
catches for API/network/cache fallbacks are left unchanged — those are defensive
by design and narrowing them risks missing edge cases.

## Changes

### 1. `cli/main.py` — theme loading (line ~178)

`except Exception` → `except (FileNotFoundError, ValueError, yaml.YAMLError)`.
Add `import yaml`.

### 2. `cli/main.py` — mock data loading (line ~113)

`except Exception` → `except (OSError, ValueError)`. Covers
`FileNotFoundError`, `PermissionError` (via `OSError`) and
`json.JSONDecodeError`, `UnicodeDecodeError` (via `ValueError`).

### 3. `cli/runtime.py` — dark theme loading (line ~150)

`except Exception` → `except (FileNotFoundError, ValueError, yaml.YAMLError)`.
Add `import yaml`.

### 4. `render/mkdocs.py` — ZoneInfo timezone (line ~93)

`except Exception` → `except KeyError`. `ZoneInfoNotFoundError` is a `KeyError`
subclass.

## Out of scope

Broad catches in `adapters/unifi.py` (API retry loops, cache I/O, fetch
fallbacks), `cli/runtime.py` (topology build, network fetch), `cli/render.py`
(device loading, WAN network fetch), and `io/paths.py` (`Path.home()`). These
are intentionally defensive for graceful degradation.
