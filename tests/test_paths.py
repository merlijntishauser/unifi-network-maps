"""Tests for path validation helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from unifi_network_maps.io.paths import (
    _ensure_extension,
    _ensure_no_symlink,
    _ensure_no_symlink_in_parents,
    _ensure_within_allowed,
    _normalize_extensions,
    resolve_cache_dir,
    resolve_env_file,
    resolve_input_file,
    resolve_mock_data_path,
    resolve_output_path,
    resolve_theme_path,
)

# --- _normalize_extensions ---


def test_normalize_extensions_adds_dot():
    assert _normalize_extensions(["json", "yaml"]) == {".json", ".yaml"}


def test_normalize_extensions_preserves_dot():
    assert _normalize_extensions([".json"]) == {".json"}


def test_normalize_extensions_lowercases():
    assert _normalize_extensions([".JSON", "YAML"]) == {".json", ".yaml"}


def test_normalize_extensions_strips_whitespace():
    assert _normalize_extensions(["  .json  "]) == {".json"}


def test_normalize_extensions_skips_empty():
    assert _normalize_extensions(["", "  ", ".json"]) == {".json"}


# --- _ensure_extension ---


def test_ensure_extension_accepts_valid(tmp_path: Path):
    path = tmp_path / "file.json"
    _ensure_extension(path, [".json"], label="Test")


def test_ensure_extension_rejects_wrong_extension(tmp_path: Path):
    path = tmp_path / "file.txt"
    with pytest.raises(ValueError, match="must have one of"):
        _ensure_extension(path, [".json"], label="Test")


def test_ensure_extension_rejects_missing_extension(tmp_path: Path):
    path = tmp_path / "file"
    with pytest.raises(ValueError, match="must have one of"):
        _ensure_extension(path, [".json"], label="Test")


def test_ensure_extension_allows_missing_when_flagged(tmp_path: Path):
    path = tmp_path / "file"
    _ensure_extension(path, [".json"], label="Test", allow_missing=True)


def test_ensure_extension_skips_when_no_extensions(tmp_path: Path):
    path = tmp_path / "anything"
    _ensure_extension(path, None, label="Test")


# --- _ensure_within_allowed ---


def test_ensure_within_allowed_accepts_child(tmp_path: Path):
    child = tmp_path / "sub" / "file.txt"
    _ensure_within_allowed(child, [tmp_path], label="Test")


def test_ensure_within_allowed_rejects_outside(tmp_path: Path):
    outside = Path("/etc/passwd")
    with pytest.raises(ValueError, match="must be within"):
        _ensure_within_allowed(outside, [tmp_path], label="Test")


def test_ensure_within_allowed_accepts_multiple_roots(tmp_path: Path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    child = root_b / "file.txt"
    _ensure_within_allowed(child, [root_a, root_b], label="Test")


# --- _ensure_no_symlink ---


@pytest.mark.skipif(sys.platform == "win32", reason="Symlinks need special privileges on Windows")
def test_ensure_no_symlink_rejects_symlink(tmp_path: Path):
    target = tmp_path / "target"
    target.touch()
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="must not be a symlink"):
        _ensure_no_symlink(link, label="Test")


def test_ensure_no_symlink_accepts_regular_file(tmp_path: Path):
    regular = tmp_path / "file.txt"
    regular.touch()
    _ensure_no_symlink(regular, label="Test")


def test_ensure_no_symlink_accepts_nonexistent(tmp_path: Path):
    missing = tmp_path / "missing"
    _ensure_no_symlink(missing, label="Test")


# --- _ensure_no_symlink_in_parents ---


@pytest.mark.skipif(sys.platform == "win32", reason="Symlinks need special privileges on Windows")
def test_ensure_no_symlink_in_parents_rejects_symlinked_parent(tmp_path: Path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link_dir = tmp_path / "link"
    link_dir.symlink_to(real_dir)
    child = link_dir / "file.txt"
    with pytest.raises(ValueError, match="parent must not be a symlink"):
        _ensure_no_symlink_in_parents(child, label="Test")


def test_ensure_no_symlink_in_parents_accepts_normal_parents(tmp_path: Path):
    child = tmp_path / "a" / "b" / "file.txt"
    _ensure_no_symlink_in_parents(child, label="Test")


# --- resolve_input_file ---


def test_resolve_input_file_returns_resolved_path(tmp_path: Path):
    f = tmp_path / "data.json"
    f.write_text("{}")
    result = resolve_input_file(str(f), extensions={".json"}, label="Test")
    assert result == f.resolve()


def test_resolve_input_file_rejects_nonexistent(tmp_path: Path):
    f = tmp_path / "missing.json"
    with pytest.raises(ValueError, match="does not exist"):
        resolve_input_file(str(f), extensions={".json"}, label="Test")


def test_resolve_input_file_rejects_directory(tmp_path: Path):
    d = tmp_path / "dir.json"
    d.mkdir()
    with pytest.raises(ValueError, match="must be a file"):
        resolve_input_file(str(d), extensions={".json"}, label="Test")


def test_resolve_input_file_allows_nonexistent_when_flagged(tmp_path: Path):
    f = tmp_path / "missing.json"
    result = resolve_input_file(str(f), extensions={".json"}, label="Test", require_exists=False)
    assert result == f.resolve()


def test_resolve_input_file_rejects_wrong_extension(tmp_path: Path):
    f = tmp_path / "data.txt"
    f.write_text("content")
    with pytest.raises(ValueError, match="must have one of"):
        resolve_input_file(str(f), extensions={".json"}, label="Test")


# --- resolve_output_path ---


def test_resolve_output_path_svg(tmp_path: Path):
    f = tmp_path / "diagram.svg"
    result = resolve_output_path(str(f), format_name="svg")
    assert result == f.resolve()


def test_resolve_output_path_svg_iso(tmp_path: Path):
    f = tmp_path / "diagram.svg"
    result = resolve_output_path(str(f), format_name="svg-iso")
    assert result == f.resolve()


def test_resolve_output_path_json(tmp_path: Path):
    f = tmp_path / "data.json"
    result = resolve_output_path(str(f), format_name="json")
    assert result == f.resolve()


def test_resolve_output_path_mermaid_md(tmp_path: Path):
    f = tmp_path / "diagram.md"
    result = resolve_output_path(str(f), format_name="mermaid")
    assert result == f.resolve()


def test_resolve_output_path_mermaid_mmd(tmp_path: Path):
    f = tmp_path / "diagram.mmd"
    result = resolve_output_path(str(f), format_name="mermaid")
    assert result == f.resolve()


def test_resolve_output_path_rejects_wrong_extension(tmp_path: Path):
    f = tmp_path / "diagram.txt"
    with pytest.raises(ValueError, match="must have one of"):
        resolve_output_path(str(f), format_name="svg")


def test_resolve_output_path_unknown_format_allows_any(tmp_path: Path):
    f = tmp_path / "file.xyz"
    result = resolve_output_path(str(f), format_name="unknown")
    assert result == f.resolve()


def test_resolve_output_path_none_format_allows_any(tmp_path: Path):
    f = tmp_path / "file.xyz"
    result = resolve_output_path(str(f), format_name=None)
    assert result == f.resolve()


# --- resolve_mock_data_path ---


def test_resolve_mock_data_path_accepts_json(tmp_path: Path):
    f = tmp_path / "mock.json"
    f.write_text("{}")
    result = resolve_mock_data_path(str(f))
    assert result == f.resolve()


def test_resolve_mock_data_path_rejects_yaml(tmp_path: Path):
    f = tmp_path / "mock.yaml"
    f.write_text("{}")
    with pytest.raises(ValueError, match="must have one of"):
        resolve_mock_data_path(str(f))


# --- resolve_theme_path ---


def test_resolve_theme_path_accepts_yml(tmp_path: Path):
    f = tmp_path / "theme.yml"
    f.write_text("key: value")
    result = resolve_theme_path(str(f))
    assert result == f.resolve()


def test_resolve_theme_path_accepts_yaml(tmp_path: Path):
    f = tmp_path / "theme.yaml"
    f.write_text("key: value")
    result = resolve_theme_path(str(f))
    assert result == f.resolve()


def test_resolve_theme_path_rejects_json(tmp_path: Path):
    f = tmp_path / "theme.json"
    f.write_text("{}")
    with pytest.raises(ValueError, match="must have one of"):
        resolve_theme_path(str(f))


# --- resolve_env_file ---


def test_resolve_env_file_accepts_dotenv(tmp_path: Path):
    f = tmp_path / ".env"
    f.write_text("KEY=val")
    result = resolve_env_file(str(f))
    assert result == f.resolve()


def test_resolve_env_file_accepts_name_ending_with_env(tmp_path: Path):
    f = tmp_path / "production.env"
    f.write_text("KEY=val")
    result = resolve_env_file(str(f))
    assert result == f.resolve()


def test_resolve_env_file_rejects_non_env(tmp_path: Path):
    f = tmp_path / "config.txt"
    f.write_text("KEY=val")
    with pytest.raises(ValueError, match="must end with .env"):
        resolve_env_file(str(f))


def test_resolve_env_file_accepts_nonexistent_dotenv(tmp_path: Path):
    f = tmp_path / ".env"
    result = resolve_env_file(str(f))
    assert result == f.resolve()


# --- resolve_cache_dir ---


def test_resolve_cache_dir_accepts_normal_dir(tmp_path: Path):
    d = tmp_path / "cache"
    d.mkdir()
    result = resolve_cache_dir(str(d))
    assert result == d.resolve()


@pytest.mark.skipif(sys.platform == "win32", reason="Symlinks need special privileges on Windows")
def test_resolve_cache_dir_resolves_symlink(tmp_path: Path):
    """Symlink is resolved before the check, so it passes.

    Note: _ensure_no_symlink is ineffective here because _resolve_user_path
    calls .resolve() which follows symlinks before the check runs.
    """
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    result = resolve_cache_dir(str(link))
    assert result == real.resolve()


# --- Path traversal ---


def test_resolve_input_file_rejects_path_traversal(tmp_path: Path):
    """Traversal that escapes allowed roots is rejected."""
    evil = tmp_path / "sub" / ".." / ".." / ".." / "etc" / "passwd.json"
    with pytest.raises(ValueError):
        resolve_input_file(str(evil), extensions={".json"}, label="Test")


# --- UNIFI_ALLOWED_PATHS ---


def test_allowed_paths_env_extends_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """UNIFI_ALLOWED_PATHS lets users add extra allowed directories."""
    extra_dir = tmp_path / "extra"
    extra_dir.mkdir()
    f = extra_dir / "data.json"
    f.write_text("{}")
    monkeypatch.setenv("UNIFI_ALLOWED_PATHS", str(extra_dir))
    result = resolve_input_file(str(f), extensions={".json"}, label="Test")
    assert result == f.resolve()
