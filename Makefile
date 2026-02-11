.PHONY: venv install lint format typecheck complexity test test-unit test-integration test-contract \
        test-acceptance bdd coverage smoketest smoketest-mock smoketest-validate visual-regression \
        visual-baselines mock-data update-examples ci version version-sync version-bump theme-matrix \
        docs docs-serve help

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

complexity:
	@echo "=== Cyclomatic Complexity (C+ rated functions) ==="
	@$(VENV)/radon cc src/unifi_network_maps -a -nc -s
	@echo ""
	@echo "=== Maintainability Index (B or lower) ==="
	@$(VENV)/radon mi src/unifi_network_maps -s -nb
	@echo ""
	@echo "=== Threshold Checks (max function: 12, max module avg: B, overall avg: A) ==="
	$(VENV)/xenon src/unifi_network_maps --max-absolute C --max-modules B --max-average A
	@./scripts/check_complexity.sh 12

# Testing
test:
	$(VENV)/pytest

test-unit:
	$(VENV)/pytest -m unit

test-integration:
	$(VENV)/pytest -m integration

test-contract:
	$(VENV)/pytest -m contract

test-acceptance:
	$(VENV)/pytest -m acceptance

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
	@$(CLI) --mock-data examples/mock_data.json --format inventory --only-unifi --output smoketest-mock/inventory.md
	@# Theme variants
	@$(CLI) --mock-data examples/mock_data.json --theme unifi --format svg-iso --output smoketest-mock/theme_unifi_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme unifi-dark --format svg-iso --output smoketest-mock/theme_unifi_dark_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme minimal --format svg-iso --output smoketest-mock/theme_minimal_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme unifi --stdout > smoketest-mock/theme_unifi.mmd
	@# Icon set variants
	@$(CLI) --mock-data examples/mock_data.json --format svg-iso --icon-set isometric --output smoketest-mock/iconset_isometric_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --format svg-iso --icon-set modern --output smoketest-mock/iconset_modern_iso.svg
	@# Dark themes with ports, wired clients, WAN info (modern icon set)
	@$(CLI) --mock-data examples/mock_data.json --theme unifi-dark --format svg --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set modern --output smoketest-mock/theme_unifi_dark_ports_wan_modern.svg
	@$(CLI) --mock-data examples/mock_data.json --theme unifi-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set modern --output smoketest-mock/theme_unifi_dark_ports_wan_modern_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme classic-dark --format svg --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set modern --output smoketest-mock/theme_classic_dark_ports_wan_modern.svg
	@$(CLI) --mock-data examples/mock_data.json --theme classic-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set modern --output smoketest-mock/theme_classic_dark_ports_wan_modern_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme minimal-dark --format svg --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set modern --output smoketest-mock/theme_minimal_dark_ports_wan_modern.svg
	@$(CLI) --mock-data examples/mock_data.json --theme minimal-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set modern --output smoketest-mock/theme_minimal_dark_ports_wan_modern_iso.svg
	@# Dark themes with ports, wired clients, WAN info (isometric icon set)
	@$(CLI) --mock-data examples/mock_data.json --theme unifi-dark --format svg --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set isometric --output smoketest-mock/theme_unifi_dark_ports_wan_isometric.svg
	@$(CLI) --mock-data examples/mock_data.json --theme unifi-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set isometric --output smoketest-mock/theme_unifi_dark_ports_wan_isometric_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme classic-dark --format svg --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set isometric --output smoketest-mock/theme_classic_dark_ports_wan_isometric.svg
	@$(CLI) --mock-data examples/mock_data.json --theme classic-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set isometric --output smoketest-mock/theme_classic_dark_ports_wan_isometric_iso.svg
	@$(CLI) --mock-data examples/mock_data.json --theme minimal-dark --format svg --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set isometric --output smoketest-mock/theme_minimal_dark_ports_wan_isometric.svg
	@$(CLI) --mock-data examples/mock_data.json --theme minimal-dark --format svg-iso --include-ports --include-clients --client-scope wired --wan-label "Odido" --wan-speed "1 Gbps ↓↑" --icon-set isometric --output smoketest-mock/theme_minimal_dark_ports_wan_isometric_iso.svg

smoketest-validate:
	@$(VENV)/pytest tests/test_smoketest_validation.py -q

visual-regression:
	@$(VENV)/pytest tests/test_visual_regression.py -v

visual-baselines:
	@$(VENV)/pytest tests/test_visual_regression.py --update-baselines

mock-data:
	@$(CLI) --generate-mock examples/mock_data.json --mock-seed 1337
	@$(CLI) --mock-data examples/mock_data.json --include-ports --include-clients --format svg-iso --output examples/output/network_ports_clients_iso.svg

update-examples:
	@mkdir -p examples/output
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

theme-matrix:
	@PYTHONPATH=src $(VENV)/python scripts/generate_theme_matrix.py

# Docs
docs:
	$(VENV)/mkdocs build

docs-serve:
	$(VENV)/mkdocs serve

# Help
help:
	@$(CLI) --help
