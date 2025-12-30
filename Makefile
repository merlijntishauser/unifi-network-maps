.PHONY: venv install lint format ci

venv:
	python -m venv .venv

install:
	.venv/bin/pip install -e .
	.venv/bin/pip install pre-commit

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff format .

ci: lint format
	.venv/bin/pre-commit run --all-files
	.venv/bin/python -m unifi_mermaid.cli --help
