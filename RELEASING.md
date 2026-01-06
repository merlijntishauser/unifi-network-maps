# Releasing

## Checklist

1) Ensure `README.md`, `CHANGELOG.md`, and `VERSION` are up to date.
2) Run tests and lint locally:
   ```bash
   ruff check .
   pytest
   ```
3) Build the package:
   ```bash
   python -m pip install -r requirements-build.txt
   python -m pip install build twine -c constraints.txt
   python -m build
   ```
4) Inspect the artifacts:
   ```bash
   python -m twine check dist/*
   ```
5) Tag the release:
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
6) Upload to PyPI:
   ```bash
   twine upload dist/*
   ```
