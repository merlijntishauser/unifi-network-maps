"""Path validation helpers for user-supplied file system inputs."""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

logger = logging.getLogger(__name__)


def _safe_home_dir() -> Path | None:
    try:
        return Path.home().resolve()
    except Exception:
        return None


def _base_roots() -> list[Path]:
    roots = [Path.cwd().resolve()]
    home = _safe_home_dir()
    if home:
        roots.append(home)
    try:
        roots.append(Path(tempfile.gettempdir()).resolve())
    except OSError as exc:
        # Best-effort temp dir; resolution can fail in restricted environments.
        logger.debug("Failed to resolve temp directory: %s", exc)
    return roots


def _extra_roots_from_env() -> list[Path]:
    extra = os.environ.get("UNIFI_ALLOWED_PATHS", "")
    roots: list[Path] = []
    if extra:
        for raw in extra.split(os.pathsep):
            raw = raw.strip()
            if raw:
                roots.append(Path(raw).expanduser().resolve())
    return roots


def _allowed_roots() -> tuple[Path, ...]:
    roots = _base_roots() + _extra_roots_from_env()
    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return tuple(unique)


def _resolve_user_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _ensure_within_allowed(path: Path, roots: Iterable[Path], *, label: str) -> None:
    for root in roots:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        else:
            return
    root_list = ", ".join(str(root) for root in roots)
    raise ValueError(f"{label} must be within: {root_list}")


def _ensure_no_symlink(path: Path, *, label: str) -> None:
    if path.exists() and path.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {path}")


def _ensure_no_symlink_in_parents(path: Path, *, label: str) -> None:
    for parent in path.parents:
        if parent.exists() and parent.is_symlink():
            raise ValueError(f"{label} parent must not be a symlink: {parent}")


def _normalize_extensions(extensions: Iterable[str]) -> set[str]:
    normalized = set()
    for ext in extensions:
        ext = ext.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = f".{ext}"
        normalized.add(ext)
    return normalized


def _ensure_extension(
    path: Path,
    extensions: Iterable[str] | None,
    *,
    label: str,
    allow_missing: bool = False,
) -> None:
    if not extensions:
        return
    allowed = _normalize_extensions(extensions)
    suffix = path.suffix.lower()
    if not suffix:
        if allow_missing:
            return
        raise ValueError(f"{label} must have one of: {', '.join(sorted(allowed))}")
    if suffix not in allowed:
        raise ValueError(f"{label} must have one of: {', '.join(sorted(allowed))}")


def resolve_input_file(
    path: str | Path,
    *,
    extensions: Iterable[str] | None,
    label: str,
    require_exists: bool = True,
) -> Path:
    resolved = _resolve_user_path(path)
    _ensure_within_allowed(resolved, _allowed_roots(), label=label)
    _ensure_extension(resolved, extensions, label=label)
    if require_exists:
        if not resolved.exists():
            raise ValueError(f"{label} does not exist: {resolved}")
        if not resolved.is_file():
            raise ValueError(f"{label} must be a file: {resolved}")
    return resolved


def resolve_output_file(
    path: str | Path,
    *,
    extensions: Iterable[str] | None,
    label: str,
    allow_missing_extension: bool = False,
) -> Path:
    resolved = _resolve_user_path(path)
    _ensure_within_allowed(resolved, _allowed_roots(), label=label)
    _ensure_extension(
        resolved,
        extensions,
        label=label,
        allow_missing=allow_missing_extension,
    )
    return resolved


def resolve_env_file(path: str | Path) -> Path:
    resolved = _resolve_user_path(path)
    _ensure_within_allowed(resolved, _allowed_roots(), label="Env file")
    if not (resolved.name.startswith(".env") or resolved.name.endswith(".env")):
        raise ValueError("Env file must end with .env")
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"Env file must be a file: {resolved}")
    return resolved


def resolve_mock_data_path(path: str | Path, *, require_exists: bool = True) -> Path:
    return resolve_input_file(
        path,
        extensions={".json"},
        label="Mock data file",
        require_exists=require_exists,
    )


def resolve_theme_path(path: str | Path, *, require_exists: bool = True) -> Path:
    return resolve_input_file(
        path,
        extensions={".yml", ".yaml"},
        label="Theme file",
        require_exists=require_exists,
    )


def resolve_output_path(path: str | Path, *, format_name: str | None) -> Path:
    extensions: set[str] | None
    if format_name == "svg" or format_name == "svg-iso":
        extensions = {".svg"}
    elif format_name in {"mock", "json"}:
        extensions = {".json"}
    elif format_name == "mermaid":
        extensions = {".md", ".mermaid", ".mmd"}
    elif format_name == "lldp-md":
        extensions = {".md"}
    elif format_name == "mkdocs":
        extensions = {".md"}
    else:
        extensions = None
    return resolve_output_file(path, extensions=extensions, label="Output file")


def resolve_cache_dir(path: str | Path) -> Path:
    resolved = _resolve_user_path(path)
    _ensure_within_allowed(resolved, _allowed_roots(), label="Cache directory")
    _ensure_no_symlink(resolved, label="Cache directory")
    _ensure_no_symlink_in_parents(resolved, label="Cache directory")
    return resolved
