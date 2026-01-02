.PHONY: venv install lint format test coverage smoketest ci version version-bump

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
	@mkdir -p smoketest
	.venv/bin/python -m unifi_mermaid.cli --stdout > smoketest/network.mmd
	.venv/bin/python -m unifi_mermaid.cli --markdown --output smoketest/network.md
	.venv/bin/python -m unifi_mermaid.cli --group-by-type --stdout > smoketest/network_grouped.mmd
	.venv/bin/python -m unifi_mermaid.cli --include-ports --include-clients --stdout > smoketest/network_ports_clients.mmd
	.venv/bin/python -m unifi_mermaid.cli --legend-only --stdout > smoketest/legend.mmd
	.venv/bin/python -m unifi_mermaid.cli --format svg --output smoketest/network.svg
	.venv/bin/python -m unifi_mermaid.cli --format svg-iso --output smoketest/network_iso.svg
	.venv/bin/python -m unifi_mermaid.cli --include-clients --format svg --output smoketest/network_clients.svg
	.venv/bin/python -m unifi_mermaid.cli --include-clients --format svg-iso --output smoketest/network_clients_iso.svg

version:
	@echo $(VERSION)

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
	printf "__version__ = \"%s\"\n" "$$next" > src/unifi_mermaid/__init__.py; \
	git add $(VERSION_FILE) src/unifi_mermaid/__init__.py; \
	git commit -m "Bump version to $$next"; \
	git tag -a "v$$next" -m "v$$next"; \
	git push origin HEAD; \
	git push origin "v$$next"

ci: lint format test
	.venv/bin/pre-commit run --all-files
	.venv/bin/python -m unifi_mermaid.cli --help
