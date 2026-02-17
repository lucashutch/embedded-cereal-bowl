"""Tests for CRLF checker utility."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.embedded_cereal_bowl.check_crlf import (
    check_crlf_in_root,
    has_crlf_endings,
    main,
    resolve_ignore_dirs,
    scan_directory,
)


def test_max_width_fallback():
    """Test MAX_WIDTH fallback when shutil.get_terminal_size fails."""
    with patch("shutil.get_terminal_size", side_effect=OSError):
        import importlib

        import src.embedded_cereal_bowl.check_crlf as check_crlf

        importlib.reload(check_crlf)
        assert check_crlf.MAX_WIDTH == 80


def test_scan_directory_permission_error(capsys):
    """Test scan_directory handling of PermissionError."""
    with patch("pathlib.Path.iterdir", side_effect=PermissionError):
        files = list(scan_directory(Path("/fake"), set()))
        assert files == []
        captured = capsys.readouterr()
        assert "Permission denied" in captured.out


def test_check_crlf_in_root_verbose(tmp_path, capsys):
    """Test check_crlf_in_root with verbose output and ignored directories."""
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()

    with patch("sys.exit") as mock_exit:
        check_crlf_in_root(tmp_path, ["ignored"], verbose=True)

    captured = capsys.readouterr()
    assert "Ignored Directories" in captured.out
    assert str(ignored_dir.resolve()) in captured.out


def test_main_with_args():
    """Test main function with command line arguments."""
    with patch("sys.argv", ["check_crlf", "/some/path", "--ignore", "build", "-v"]):
        with patch(
            "src.embedded_cereal_bowl.check_crlf.check_crlf_in_root"
        ) as mock_check:
            main()
            mock_check.assert_called_once()
            # Check arguments passed to check_crlf_in_root
            args, kwargs = mock_check.call_args
            assert kwargs["repo_path"] == Path("/some/path").resolve()
            assert kwargs["ignore_patterns"] == ["build"]
            assert kwargs["verbose"] is True


def test_scan_directory_symlink(tmp_path):
    """Test scan_directory skips symlinks."""
    target = tmp_path / "target.txt"
    target.write_text("content")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    files = list(scan_directory(tmp_path, set()))
    assert target in files
    assert link not in files


def test_main_block():
    """Test the if __name__ == '__main__': block."""
    import runpy

    with patch("sys.argv", ["check_crlf", "--version"]):
        # This will call argparse which will try to exit
        with pytest.raises(SystemExit):
            runpy.run_module("src.embedded_cereal_bowl.check_crlf", run_name="__main__")


def test_has_crlf_endings_true(tmp_path):
    f = tmp_path / "crlf.txt"
    f.write_bytes(b"line1\r\nline2\r\n")
    assert has_crlf_endings(f) is True


def test_has_crlf_endings_false_unix(tmp_path):
    f = tmp_path / "unix.txt"
    f.write_bytes(b"line1\nline2\n")
    assert has_crlf_endings(f) is False


def test_has_crlf_endings_binary(tmp_path):
    f = tmp_path / "binary.bin"
    f.write_bytes(b"line1\r\n\0binary")
    assert has_crlf_endings(f) is False


def test_has_crlf_endings_error(tmp_path, capsys):
    f = tmp_path / "error.txt"
    # File doesn't exist
    assert has_crlf_endings(f) is False
    captured = capsys.readouterr()
    assert "Error reading file" in captured.out


def test_scan_directory(tmp_path):
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir2").mkdir()
    f1 = tmp_path / "dir1" / "file1.txt"
    f1.write_text("content")
    f2 = tmp_path / "dir2" / "file2.txt"
    f2.write_text("content")

    files = list(scan_directory(tmp_path, {tmp_path / "dir2"}))
    assert f1 in files
    assert f2 not in files


def test_resolve_ignore_dirs(tmp_path):
    d1 = tmp_path / "build"
    d1.mkdir()
    d2 = tmp_path / "dist"
    d2.mkdir()
    f1 = tmp_path / "file.txt"
    f1.write_text("content")

    ignored = resolve_ignore_dirs(tmp_path, ["build", "dist", "file.txt"])
    assert d1.resolve() in ignored
    assert d2.resolve() in ignored
    assert f1.resolve() not in ignored  # Only dirs are ignored


def test_check_crlf_in_root_not_dir(capsys):
    with pytest.raises(SystemExit) as excinfo:
        check_crlf_in_root(Path("non_existent_dir_12345"), [])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Directory not found" in captured.out


def test_check_crlf_in_root_clean(tmp_path, capsys):
    f = tmp_path / "clean.txt"
    f.write_bytes(b"unix\n")

    with pytest.raises(SystemExit) as excinfo:
        check_crlf_in_root(tmp_path, [])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "No files with CRLF line endings were found" in captured.out


def test_check_crlf_in_root_found(tmp_path, capsys):
    f = tmp_path / "dirty.txt"
    f.write_bytes(b"windows\r\n")

    with pytest.raises(SystemExit) as excinfo:
        check_crlf_in_root(tmp_path, [])
    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    assert "Found files with CRLF line endings" in captured.out
    assert "dirty.txt" in captured.out


def test_main_keyboard_interrupt():
    with patch(
        "src.embedded_cereal_bowl.check_crlf.check_crlf_in_root",
        side_effect=KeyboardInterrupt,
    ):
        with patch("sys.argv", ["check_crlf"]):
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 130
