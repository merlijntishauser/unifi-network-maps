.PHONY: venv install lint format test ci

venv:
	python -m venv .venv

install:
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff format .

test:
	.venv/bin/pytest

ci: lint format test
	.venv/bin/pre-commit run --all-files
	.venv/bin/python -m unifi_mermaid.cli --help
