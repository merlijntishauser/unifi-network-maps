# Refactor: Reuse coerce_lldp() in unifi.py serialization

Addresses [#28](https://github.com/merlijntishauser/unifi-network-maps/issues/28).

## Problem

`_serialize_lldp_entry()` in `adapters/unifi.py` duplicates the field-extraction
logic of `coerce_lldp()` in `model/lldp.py`. Both extract the same five LLDP
fields with the same alternative key names. Additionally, `lldp.py` has a local
`_get_field()` helper that duplicates the shared `first_attr()` from
`model/helpers.py`.

## Changes

### 1. `model/lldp.py` -- replace `_get_field()` with `first_attr()`

- Remove the local `_get_field()` function.
- Import `first_attr` from `model.helpers`.
- Replace the five `_get_field()` calls in `coerce_lldp()` with `first_attr()`.

### 2. `adapters/unifi.py` -- replace `_serialize_lldp_entry()` with `coerce_lldp()` + `lldp_entry_to_dict()`

- Import `coerce_lldp` from `model.lldp` and `lldp_entry_to_dict` from
  `model.snapshot`.
- Delete `_serialize_lldp_entry()`.
- Rewrite `_serialize_lldp_entries()` to call `coerce_lldp(entry)` (catching
  `ValueError` for entries missing required fields) then `lldp_entry_to_dict()`
  for serialization.

## Out of scope

Moving other cache-serialization helpers (`_serialize_port_entry`,
`_serialize_device_for_cache`, etc.) out of `unifi.py`. Those deal with raw API
response objects, a different concern from `snapshot.py` which serializes typed
model dataclasses.

## Net result

- ~20 lines removed, 2 functions eliminated, 1 duplicate helper removed.
- Single source of truth for LLDP field extraction.
