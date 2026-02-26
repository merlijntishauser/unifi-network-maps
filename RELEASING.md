# Releasing

## Automated Publish

Pushing a version tag triggers the GitHub Actions publish workflow, which waits for CI to pass, then builds and uploads to PyPI using OIDC trusted publishing.

## Checklist

1. Ensure `README.md` and `CHANGELOG.md` are up to date.

2. Run all checks locally:
   ```bash
   make ci
   ```

3. Bump version, commit, tag, and push:
   ```bash
   make version-bump
   ```
   This updates `VERSION`, `pyproject.toml`, and `src/unifi_network_maps/__init__.py`, commits, tags, and pushes.

4. Verify the [publish workflow](https://github.com/merlijntishauser/unifi-network-maps/actions/workflows/publish.yml) completes successfully.

5. Verify the package on [PyPI](https://pypi.org/project/unifi-network-maps/).

## Manual Publish (fallback)

If the workflow fails, build and upload manually:

```bash
python -m pip install -r requirements-build.txt
python -m pip install build twine -c constraints.txt
python -m build
python -m twine check dist/*
twine upload dist/*
```
