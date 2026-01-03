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
	@mkdir -p smoketest
	.venv/bin/unifi-network-maps --stdout > smoketest/network.mmd
	.venv/bin/unifi-network-maps --markdown --output smoketest/network.md
	.venv/bin/unifi-network-maps --group-by-type --stdout > smoketest/network_grouped.mmd
	.venv/bin/unifi-network-maps --include-ports --include-clients --stdout > smoketest/network_ports_clients.mmd
	.venv/bin/unifi-network-maps --include-ports --stdout > smoketest/network_ports.mmd
	.venv/bin/unifi-network-maps --legend-only --stdout > smoketest/legend.mmd
	.venv/bin/unifi-network-maps --format svg --output smoketest/network.svg
	.venv/bin/unifi-network-maps --format svg-iso --output smoketest/network_iso.svg
	.venv/bin/unifi-network-maps --include-clients --format svg --output smoketest/network_clients.svg
	.venv/bin/unifi-network-maps --include-clients --format svg-iso --output smoketest/network_clients_iso.svg
	.venv/bin/unifi-network-maps --include-ports --format svg --output smoketest/network_ports.svg
	.venv/bin/unifi-network-maps --include-ports --format svg-iso --output smoketest/network_ports_iso.svg
	.venv/bin/unifi-network-maps --include-ports --include-clients --format svg --output smoketest/network_ports_clients.svg
	.venv/bin/unifi-network-maps --include-ports --include-clients --format svg-iso --output smoketest/network_ports_clients_iso.svg

version:
	@echo $(VERSION)

version-sync:
	@python3 -c 'from pathlib import Path; v=Path("$(VERSION_FILE)").read_text().strip(); \
py=Path("pyproject.toml"); \
text=py.read_text(encoding="utf-8"); \
import re; \
text=re.sub(r"^version\\s*=\\s*\\\"[^\\\"]+\\\"", f"version = \\\"{v}\\\"", text, flags=re.M); \
py.write_text(text, encoding="utf-8"); \
Path("src/unifi_mermaid/__init__.py").write_text(f"__version__ = \"{v}\"\n", encoding="utf-8")'

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
	python3 -c 'import re,sys; v=sys.argv[1]; \
py="pyproject.toml"; \
text=open(py, encoding="utf-8").read(); \
text=re.sub(r"^version\\s*=\\s*\\\"[^\\\"]+\\\"", f"version = \\\"{v}\\\"", text, flags=re.M); \
open(py, "w", encoding="utf-8").write(text); \
open("src/unifi_mermaid/__init__.py", "w", encoding="utf-8").write(f"__version__ = \\\"{v}\\\"\\n")' "$$next"; \
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
	.venv/bin/unifi-network-maps --help
