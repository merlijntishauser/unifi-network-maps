# Contributing

Thanks for considering a contribution!

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-build.txt
pip install -r requirements-dev.txt -c constraints.txt
pre-commit install
```

Editable install:

```bash
pip install -e .
```

Local install check (non-editable):

```bash
pip install .
```

## Running checks

```bash
ruff check .
pyright
pytest
behave
```

Or run everything with:

```bash
make ci
```

Notes:
- Contract tests use fixtures in `tests/test_contract_unifi.py` and run in CI.
- Live contract tests require `UNIFI_CONTRACT_LIVE=1` plus UniFi env vars.
- BDD tests live in `features/` and run via `behave` (included in `make ci`).

## Release

Build and upload to PyPI:

```bash
python -m pip install build twine
python -m build
twine upload dist/*
```

Tagging is recommended before release:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

See `LICENSES.md` for third-party license info.

## Guidelines

- Keep changes focused and small.
- Add or update tests where behavior changes.
- Run `make ci` before opening a PR.
