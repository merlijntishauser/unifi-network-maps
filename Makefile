.PHONY: venv install lint format typecheck test bdd coverage smoketest smoketest-mock \
        smoketest-validate visual-regression visual-baselines mock-data ci version \
        version-sync version-bump help

VERSION_FILE = VERSION
VENV = .venv/bin
PYTHON ?= python
CLI = PYTHONPATH=src $(VENV)/python -m unifi_network_maps.cli

# Setup
venv:
	python -m venv .venv

install:
	$(VENV)/pip install -e ".[dev]"

# Quality
lint:
	$(VENV)/ruff check .

format:
	$(VENV)/ruff format .

typecheck:
	$(VENV)/pyright

# Testing
test:
	$(VENV)/pytest

bdd:
	$(VENV)/behave

coverage:
	$(VENV)/pytest --cov=unifi_network_maps --cov-report=term-missing

smoketest:
	@./scripts/smoketest.sh

smoketest-mock:
	@rm -rf smoketest-mock && mkdir -p smoketest-mock
	@$(CLI) --mock-data examples/mock_data.json --include-ports --stdout > smoketest-mock/network_ports.mmd
	@$(CLI) --mock-data examples/mock_data.json --include-ports --include-clients --format svg-iso --output smoketest-mock/network_ports_clients_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --format svg --svg-layout-mode grouped --output smoketest-mock/network_grouped.svg
	@$(CLI) --mock-data examples/mock_data.json --format svg-iso --svg-layout-mode grouped --output smoketest-mock/network_grouped_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --format mkdocs --include-clients --mkdocs-dual-theme --mkdocs-sidebar-legend --output smoketest-mock/unifi-network-dual-theme-and-clients.md
	@$(CLI) --mock-data examples/mock_data.json --format svg --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --output smoketest-mock/network_wan.svg
	@$(CLI) --mock-data examples/mock_data.json --format svg-iso --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --wan2-label "Backup SFP+" --output smoketest-mock/network_wan_dual_iso.svg
	@# Theme variants
	@$(CLI) --mock-data examples/mock_data.json --theme unifi --format svg-iso --output smoketest-mock/theme_unifi_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme unifi-dark --format svg-iso --output smoketest-mock/theme_unifi_dark_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme minimal --format svg-iso --output smoketest-mock/theme_minimal_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme unifi --stdout > smoketest-mock/theme_unifi.mmd

smoketest-validate:
	@$(VENV)/pytest tests/test_smoketest_validation.py -q

visual-regression:
	@$(VENV)/pytest tests/test_visual_regression.py -v

visual-baselines:
	@$(VENV)/pytest tests/test_visual_regression.py --update-baselines

mock-data:
	@$(CLI) --generate-mock examples/mock_data.json --mock-seed 1337
	@$(CLI) --mock-data examples/mock_data.json --include-ports --include-clients --format svg-iso --output examples/output/network_ports_clients_iso.svg

# CI
ci:
	@./scripts/ci.sh

# Version management
version:
	@cat $(VERSION_FILE)

version-sync:
	@python3 scripts/version_sync.py

version-bump:
	@scripts/version_bump.sh

# Help
help:
	@$(CLI) --help
