from pathlib import Path
from unittest.mock import patch

import pytest

from unifi_network_maps.io.export import _write_atomic, write_output


def test_write_output_defaults_to_stdout(capsys):
    write_output("hello", output_path=None, stdout=False)
    assert capsys.readouterr().out == "hello"


def test_write_output_writes_file(tmp_path):
    path = tmp_path / "out.txt"
    write_output("content", output_path=str(path), stdout=False)
    assert path.read_text(encoding="utf-8") == "content"


def test_write_output_both_stdout_and_file(tmp_path, capsys):
    path = tmp_path / "out.txt"
    write_output("content", output_path=str(path), stdout=True)
    assert path.read_text(encoding="utf-8") == "content"
    assert capsys.readouterr().out == "content"


def test_write_output_creates_parent_directories(tmp_path):
    path = tmp_path / "subdir" / "nested" / "out.txt"
    write_output("content", output_path=str(path), stdout=False)
    assert path.read_text(encoding="utf-8") == "content"


def test_write_output_with_format_name(tmp_path):
    path = tmp_path / "out.svg"
    write_output("content", output_path=str(path), stdout=False, format_name="svg")
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "content"


def test_write_atomic_cleans_up_on_failure(tmp_path):
    """Test that _write_atomic cleans up temp file on failure."""
    path = tmp_path / "out.txt"

    # Mock Path.replace to raise an exception
    with patch.object(Path, "replace", side_effect=PermissionError("Access denied")):
        with pytest.raises(PermissionError):
            _write_atomic(path, "content")

    # Verify no temp files left behind
    temp_files = list(tmp_path.glob(".out.txt.*"))
    assert len(temp_files) == 0


def test_write_atomic_overwrites_existing_file(tmp_path):
    """Test that atomic write properly overwrites existing content."""
    path = tmp_path / "out.txt"
    path.write_text("old content", encoding="utf-8")

    _write_atomic(path, "new content")

    assert path.read_text(encoding="utf-8") == "new content"
