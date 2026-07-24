# Plan: Device inventory table with DNS hostname resolution

## Context

Add a structured device inventory that lists all UniFi infrastructure devices (gateway, switches, APs) with model, IP, reverse-DNS hostname, MAC, and firmware. The inventory is rendered as a markdown table in MkDocs output and exposed as structured data (`list[DeviceInfo]`) for the HA integration to use in a Lovelace card.

## Data Model

### DeviceInfo dataclass

New file: `model/inventory.py`

```python
@dataclass(frozen=True)
class DeviceInfo:
    name: str
    device_type: str  # "gateway", "switch", "ap", "other"
    model_name: str
    ip: str
    hostname: str | None  # reverse DNS result, None if lookup fails
    mac: str
    firmware: str
```

### build_device_inventory()

```python
def build_device_inventory(
    devices: list[Device],
    hostnames: dict[str, str] | None = None,
) -> list[DeviceInfo]:
```

- Converts `list[Device]` to `list[DeviceInfo]`
- Joins hostname from the `hostnames` map (keyed by IP)
- Sorted by device type rank (gateway, switch, ap, other) then by name
- Exported from `model/__init__.py`

## DNS Resolution

### resolve_hostnames()

New file: `adapters/dns.py`

```python
def resolve_hostnames(
    ips: list[str],
    dns_server: str,
    timeout: float = 2.0,
) -> dict[str, str]:
    """Reverse-resolve IPs to hostnames using a specific DNS server.

    Uses dnspython to query the given dns_server for PTR records.
    Returns {ip: hostname} for successful resolutions only.
    Failures are silently skipped (logged at debug level).
    """
```

- Uses `dnspython` (hard dependency) with `dns.resolver.Resolver`
- Sets `resolver.nameservers = [dns_server]`
- Performs PTR lookups via `dns.reversename.from_address()` + `resolver.resolve()`
- Timeout per query (default 2s), failures logged at debug level and skipped
- Exported from `adapters/__init__.py`

### Dependency

Add `dnspython` to `pyproject.toml` dependencies.

## CLI Integration

### --resolve-hostnames flag

In `cli/args.py`, add to the Functional group:

```python
parser.add_argument(
    "--resolve-hostnames",
    action=argparse.BooleanOptionalAction,
    default=None,
    help="Resolve device IPs to hostnames via reverse DNS (default: on for mkdocs)",
)
```

- `--resolve-hostnames` forces on, `--no-resolve-hostnames` forces off
- `default=None` means "auto": enabled for `--format mkdocs`, disabled otherwise
- DNS server is derived from `UNIFI_URL` (extract host from URL)

### Wiring in cli/render.py

In the MkDocs and standard render paths:

1. If resolve_hostnames is enabled, extract controller host from config URL
2. Call `resolve_hostnames(device_ips, controller_host)`
3. Call `build_device_inventory(devices, hostnames)`
4. Pass `list[DeviceInfo]` to the MkDocs renderer

## MkDocs Rendering

Add an "Infrastructure" section before the existing device detail sections in the MkDocs template:

```markdown
## Infrastructure

| Name | Type | Model | IP | Hostname | MAC | Firmware |
|------|------|-------|----|----------|-----|----------|
| UDM Pro | Gateway | Dream Machine Pro | 192.168.1.1 | udm.local | aa:bb:... | 4.0.6 |
```

When hostnames are not resolved (no `--resolve-hostnames`), the Hostname column is omitted.

The `render_device_inventory_table()` function in `render/mkdocs.py` (or a new `render/inventory.py`) takes `list[DeviceInfo]` and returns a markdown table string.

## Files to modify

| File | Change |
|------|--------|
| `model/inventory.py` (new) | `DeviceInfo` dataclass, `build_device_inventory()` |
| `model/__init__.py` | Export `DeviceInfo`, `build_device_inventory` |
| `adapters/dns.py` (new) | `resolve_hostnames()` |
| `adapters/__init__.py` | Export `resolve_hostnames` |
| `cli/args.py` | Add `--resolve-hostnames` / `--no-resolve-hostnames` |
| `cli/render.py` | Wire DNS resolution into render pipeline |
| `render/mkdocs.py` + template | Add inventory table section |
| `pyproject.toml` | Add `dnspython` dependency |
| `tests/test_inventory.py` (new) | Tests for `DeviceInfo`, `build_device_inventory` |
| `tests/test_dns.py` (new) | Tests for `resolve_hostnames` (mocked DNS) |

## Testing

- `build_device_inventory()` returns correct DeviceInfo list from devices
- Hostname map is correctly joined by IP
- Missing hostnames result in `None`
- Devices sorted by type rank then name
- `resolve_hostnames()` handles successful lookups (mocked)
- `resolve_hostnames()` handles failures gracefully (mocked)
- MkDocs output contains "Infrastructure" section with table
- Hostname column omitted when no hostnames resolved
- `--resolve-hostnames` / `--no-resolve-hostnames` flags work correctly
- Auto-detection: enabled for mkdocs, disabled for other formats

## Verification

- `ruff check . && ruff format --check .`
- `pyright`
- `pytest`
- `behave`
- `make smoketest-mock && make smoketest-validate`
