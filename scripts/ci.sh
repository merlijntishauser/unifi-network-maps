#!/usr/bin/env bash
# CI runner script - summarizes output, shows details only on failure
set -e

VENV=".venv/bin"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Width for the dotted line (matches pre-commit style)
LINE_WIDTH=73

run_step() {
    local name="$1"
    shift
    local output
    local exit_code

    # Calculate dots needed to fill the line
    local name_len=${#name}
    local dots_needed=$((LINE_WIDTH - name_len))
    local dots=$(printf '.%.0s' $(seq 1 $dots_needed))

    # Print name and dots without newline
    printf "%s%s" "$name" "$dots"

    if output=$("$@" 2>&1); then
        echo -e "${GREEN}Passed${NC}"
        return 0
    else
        exit_code=$?
        echo -e "${RED}Failed${NC}"
        echo -e "${YELLOW}Output:${NC}"
        echo "$output"
        return $exit_code
    fi
}

echo "Running CI pipeline..."
echo ""

run_step "ruff" $VENV/ruff check .
run_step "ruff-format" $VENV/ruff format --check .
run_step "pyright" $VENV/pyright
run_step "xenon" $VENV/xenon src/unifi_network_maps --max-absolute C --max-modules B --max-average A
run_step "complexity-max" ./scripts/check_complexity.sh 14
run_step "pytest" $VENV/pytest -q
run_step "behave" $VENV/behave -q --no-capture
run_step "smoketest-mock" make -s smoketest-mock
run_step "smoketest-validate" $VENV/pytest tests/test_smoketest_validation.py -q

echo ""
echo -e "${GREEN}All CI checks passed!${NC}"
