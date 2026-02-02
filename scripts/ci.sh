#!/usr/bin/env bash
# CI runner script - summarizes output, shows details only on failure
set -e

VENV=".venv/bin"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

run_step() {
    local name="$1"
    shift
    local output
    local exit_code

    printf "%-30s" "$name..."

    if output=$("$@" 2>&1); then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        exit_code=$?
        echo -e "${RED}FAILED${NC}"
        echo -e "${YELLOW}Output:${NC}"
        echo "$output"
        return $exit_code
    fi
}

echo "Running CI pipeline..."
echo ""

run_step "Lint (ruff check)" $VENV/ruff check .
run_step "Format (ruff format)" $VENV/ruff format --check .
run_step "Typecheck (pyright)" $VENV/pyright
run_step "Unit tests (pytest)" $VENV/pytest -q
run_step "BDD tests (behave)" $VENV/behave -q --no-capture
run_step "Smoketest mock" make -s smoketest-mock
run_step "Smoketest validate" $VENV/pytest tests/test_smoketest_validation.py -q
run_step "Pre-commit hooks" $VENV/pre-commit run --all-files

echo ""
echo -e "${GREEN}All CI checks passed!${NC}"
