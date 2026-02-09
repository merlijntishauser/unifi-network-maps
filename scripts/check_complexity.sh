#!/usr/bin/env bash
# Check that no function exceeds complexity threshold (default: 12)
# Usage: check_complexity.sh [max_complexity]

MAX_COMPLEXITY=${1:-12}
VENV="${VENV:-.venv/bin}"

# Find functions with complexity > threshold
# Pattern matches: C (13), C (14), ..., C (20), D (any), E (any), F (any)
high_complexity=$($VENV/radon cc src/unifi_network_maps -s 2>&1 | grep -E " - C \(1[3-9]\)| - C \(20\)| - D \(| - E \(| - F \(")

if [ -n "$high_complexity" ]; then
    echo "Functions with complexity > $MAX_COMPLEXITY found:"
    echo "$high_complexity"
    exit 1
fi

exit 0
