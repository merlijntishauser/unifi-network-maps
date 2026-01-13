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
- Render helper structure is documented in `src/unifi_network_maps/render/README.md`.

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

## Is there value in this project?

  What exists today:

  - UniFi UI topology view: great live map, but not exportable, not automatable, and not Mermaid/SVG.
  - Mermaid/Graphviz tools: diagramming, but no UniFi data ingestion or LLDP/topology logic.
  - UniFi API wrappers: data access only, no rendering/export pipelines.
  - NetBox/Grafana/HA cards: broader infra tooling, but not focused on UniFi LLDP + publishable diagrams.

  What’s distinctive here:

  - Automated UniFi → Mermaid/SVG (incl. isometric) output, with ports/PoE/clients.
  - Deterministic CLI + cache + mock generator for CI and docs.
  - MkDocs/Markdown output plus a separate HA integration repo for live updates.
  - A clean render pipeline that can power multiple export targets.

  So we’re not duplicating a packaged workflow; we’re combining data + topology modeling + diagram output + documentation/export in a way I haven’t seen in one place.
  
