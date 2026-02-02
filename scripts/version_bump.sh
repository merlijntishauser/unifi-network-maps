#!/usr/bin/env bash
# Bump version interactively, sync files, commit, tag, and push
set -e

VERSION_FILE="VERSION"

current=$(cat "$VERSION_FILE")
default=$(python3 -c "
import sys
v = sys.argv[1].strip().split('.')
if len(v) != 3 or not all(p.isdigit() for p in v):
    sys.exit(1)
major, minor, patch = map(int, v)
print(f'{major}.{minor}.{patch + 1}')
" "$current")

echo "Current version: $current"
read -p "New version [$default]: " next
next=${next:-$default}

if ! echo "$next" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Invalid semver (expected x.y.z)"
    exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Working tree not clean. Commit or stash changes first."
    exit 1
fi

printf "%s\n" "$next" > "$VERSION_FILE"
python3 scripts/version_sync.py

if ! grep -q "version = \"$next\"" pyproject.toml; then
    echo "pyproject.toml version did not update"
    exit 1
fi

git add "$VERSION_FILE" src/unifi_network_maps/__init__.py pyproject.toml
git commit -m "Bump version to $next"
git tag -a "v$next" -m "v$next"
git push origin HEAD
git push origin "v$next"

echo "Version bumped to $next"
