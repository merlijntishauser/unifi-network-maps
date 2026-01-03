# Contributing

Thanks for considering a contribution!

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Running checks

```bash
ruff check .
pytest
```

## Guidelines

- Keep changes focused and small.
- Add or update tests where behavior changes.
- Run `ruff` and `pytest` before opening a PR.
