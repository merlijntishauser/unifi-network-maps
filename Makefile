.PHONY: venv install lint format test coverage smoketest smoketest-mock mock-data ci version version-sync version-bump help

VERSION_FILE = VERSION
PYTHON ?= python

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

coverage:
	.venv/bin/pytest --cov=unifi_network_maps --cov-report=term-missing

smoketest:
	@rm -rf smoketest
	@mkdir -p smoketest/lldp smoketest/mermaid smoketest/mkdocs smoketest/svg smoketest/svg-iso smoketest/themes
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --stdout > smoketest/mermaid/network.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --markdown --output smoketest/mermaid/network.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --group-by-type --stdout > smoketest/mermaid/network_grouped.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-ports --include-clients --stdout > smoketest/mermaid/network_ports_clients.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --client-scope wireless --stdout > smoketest/mermaid/network_clients_wireless.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --client-scope all --stdout > smoketest/mermaid/network_clients_all.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-ports --stdout > smoketest/mermaid/network_ports.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --legend-only --stdout > smoketest/mermaid/legend.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format mkdocs --output smoketest/mkdocs/unifi-network.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format mkdocs --include-clients --output smoketest/mkdocs/unifi-network-clients.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format mkdocs --legend-scale 0.6 --output smoketest/mkdocs/unifi-network-legend-scaled.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format mkdocs --legend-style diagram --output smoketest/mkdocs/unifi-network-legend-diagram.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format mkdocs --mkdocs-sidebar-legend --output smoketest/mkdocs/unifi-network-sidebar-legend.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format lldp-md --output smoketest/lldp/lldp.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format lldp-md --include-clients --output smoketest/lldp/lldp_clients.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format lldp-md --include-clients --client-scope wireless --output smoketest/lldp/lldp_clients_wireless.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format lldp-md --include-clients --client-scope all --output smoketest/lldp/lldp_clients_all.md
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format svg --output smoketest/svg/network.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --format svg-iso --output smoketest/svg-iso/network_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --format svg --output smoketest/svg/network_clients.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --format svg-iso --output smoketest/svg-iso/network_clients_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --client-scope wireless --format svg --output smoketest/svg/network_clients_wireless.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --client-scope wireless --format svg-iso --output smoketest/svg-iso/network_clients_wireless_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --client-scope all --format svg --output smoketest/svg/network_clients_all.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-clients --client-scope all --format svg-iso --output smoketest/svg-iso/network_clients_all_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-ports --format svg --output smoketest/svg/network_ports.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-ports --format svg-iso --output smoketest/svg-iso/network_ports_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-ports --include-clients --format svg --output smoketest/svg/network_ports_clients.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --include-ports --include-clients --format svg-iso --output smoketest/svg-iso/network_ports_clients_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/default.yaml --stdout > smoketest/themes/mermaid_default.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/dark.yaml --stdout > smoketest/themes/mermaid_dark.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/default.yaml --legend-only --stdout > smoketest/themes/legend_default.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/dark.yaml --legend-only --stdout > smoketest/themes/legend_dark.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/default.yaml --format svg --output smoketest/themes/svg_default.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/dark.yaml --format svg --output smoketest/themes/svg_dark.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/default.yaml --format svg-iso --output smoketest/themes/svg_iso_default.svg
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --theme-file src/unifi_network_maps/assets/themes/dark.yaml --format svg-iso --output smoketest/themes/svg_iso_dark.svg

smoketest-mock:
	@rm -rf smoketest-mock
	@mkdir -p smoketest-mock
	PYTHONPATH=src $(PYTHON) -m unifi_network_maps.cli --mock-data examples/mock_data.json --include-ports --stdout > smoketest-mock/network_ports.mmd
	PYTHONPATH=src $(PYTHON) -m unifi_network_maps.cli --mock-data examples/mock_data.json --include-ports --include-clients --format svg-iso --output smoketest-mock/network_ports_clients_iso.svg

mock-data:
	PYTHONPATH=src $(PYTHON) -m unifi_network_maps.cli --generate-mock examples/mock_data.json --mock-seed 1337
	PYTHONPATH=src $(PYTHON) -m unifi_network_maps.cli --mock-data examples/mock_data.json --include-ports --include-clients --format svg-iso --output examples/output/network_ports_clients_iso.svg

version:
	@echo $(VERSION)

version-sync:
	@python3 scripts/version_sync.py

version-bump:
	@current=$$(cat $(VERSION_FILE)); \
	default=$$(python3 -c 'import sys; v=sys.argv[1].strip().split("."); \
		(len(v)==3 and all(p.isdigit() for p in v)) or sys.exit(1); \
		major,minor,patch=map(int,v); patch+=1; \
		print(f"{major}.{minor}.{patch}")' "$$current"); \
	echo "Current version: $$current"; \
	read -p "New version [$$default]: " next; \
	if [ -z "$$next" ]; then next="$$default"; fi; \
	if ! echo "$$next" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$$'; then \
		echo "Invalid semver (expected x.y.z)"; exit 1; \
	fi; \
	if ! git diff --quiet || ! git diff --cached --quiet; then \
		echo "Working tree not clean. Commit or stash changes first."; exit 1; \
	fi; \
	printf "%s\n" "$$next" > $(VERSION_FILE); \
	python3 scripts/version_sync.py; \
	if ! grep -q "version = \"$$next\"" pyproject.toml; then \
		echo "pyproject.toml version did not update"; exit 1; \
	fi; \
	git add $(VERSION_FILE) src/unifi_network_maps/__init__.py pyproject.toml; \
	git commit -m "Bump version to $$next"; \
	git tag -a "v$$next" -m "v$$next"; \
	git push origin HEAD; \
	git push origin "v$$next"

ci: lint format test
	.venv/bin/pre-commit run --all-files
	$(MAKE) help
help:
	PYTHONPATH=src .venv/bin/python -m unifi_network_maps.cli --help
