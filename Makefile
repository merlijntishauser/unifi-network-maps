.PHONY: venv install lint format test coverage smoketest ci version version-sync version-bump

VERSION_FILE = VERSION

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
	.venv/bin/pytest --cov=unifi_mermaid --cov-report=term-missing

smoketest:
	@rm -rf smoketest
	@mkdir -p smoketest/mermaid smoketest/svg smoketest/svg-iso smoketest/themes
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --stdout > smoketest/mermaid/network.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --markdown --output smoketest/mermaid/network.md
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --group-by-type --stdout > smoketest/mermaid/network_grouped.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-ports --include-clients --stdout > smoketest/mermaid/network_ports_clients.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-ports --stdout > smoketest/mermaid/network_ports.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --legend-only --stdout > smoketest/mermaid/legend.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --format svg --output smoketest/svg/network.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --format svg-iso --output smoketest/svg-iso/network_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-clients --format svg --output smoketest/svg/network_clients.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-clients --format svg-iso --output smoketest/svg-iso/network_clients_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-ports --format svg --output smoketest/svg/network_ports.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-ports --format svg-iso --output smoketest/svg-iso/network_ports_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-ports --include-clients --format svg --output smoketest/svg/network_ports_clients.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --include-ports --include-clients --format svg-iso --output smoketest/svg-iso/network_ports_clients_iso.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/default.yaml --stdout > smoketest/themes/mermaid_default.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/dark.yaml --stdout > smoketest/themes/mermaid_dark.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/default.yaml --legend-only --stdout > smoketest/themes/legend_default.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/dark.yaml --legend-only --stdout > smoketest/themes/legend_dark.mmd
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/default.yaml --format svg --output smoketest/themes/svg_default.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/dark.yaml --format svg --output smoketest/themes/svg_dark.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/default.yaml --format svg-iso --output smoketest/themes/svg_iso_default.svg
	PYTHONPATH=src .venv/bin/python -m unifi_mermaid.cli --theme-file src/unifi_mermaid/assets/themes/dark.yaml --format svg-iso --output smoketest/themes/svg_iso_dark.svg

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
	git add $(VERSION_FILE) src/unifi_mermaid/__init__.py pyproject.toml; \
	git commit -m "Bump version to $$next"; \
	git tag -a "v$$next" -m "v$$next"; \
	git push origin HEAD; \
	git push origin "v$$next"

ci: lint format test
	.venv/bin/pre-commit run --all-files
	.venv/bin/python -m unifi_mermaid.cli --help
