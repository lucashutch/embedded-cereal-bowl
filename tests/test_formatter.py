"""Tests for the formatter module."""

import concurrent.futures
import runpy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.embedded_cereal_bowl.formatter.formatter import (
    check_for_tools,
    check_format,
    find_all_files,
    format_files,
    main,
    process_files_parallel,
    process_one_file,
    resolve_ignore_dirs,
    scan_directory,
)


class TestFormatterDiscovery:
    """Test directory scanning and file discovery."""

    def test_resolve_ignore_dirs(self, tmp_path):
        (tmp_path / "build").mkdir()
        (tmp_path / "src").mkdir()
        patterns = ["build", "nonexistent"]
        result = resolve_ignore_dirs(tmp_path, patterns)
        assert result == {tmp_path / "build"}

    def test_scan_directory(self, tmp_path):
        (tmp_path / "file1.cpp").write_text("code")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file2.h").write_text("header")
        (tmp_path / "ignored").mkdir()
        (tmp_path / "ignored" / "file3.cpp").write_text("code")

        excluded = {tmp_path / "ignored"}
        result = list(scan_directory(tmp_path, excluded))
        names = {p.name for p in result}
        assert names == {"file1.cpp", "file2.h"}
        assert "file3.cpp" not in names

    def test_scan_directory_permission_error(self, capsys):
        with patch("pathlib.Path.iterdir", side_effect=PermissionError):
            assert list(scan_directory(Path("/fake"), set())) == []
            assert "Permission denied" in capsys.readouterr().err

    def test_find_all_files(self, tmp_path, capsys):
        (tmp_path / "test.cpp").write_text("code")
        (tmp_path / "CMakeLists.txt").write_text("cmake")
        (tmp_path / "ignored").mkdir()
        (tmp_path / "ignored" / "file.cpp").write_text("code")

        result = find_all_files(tmp_path, ["ignored"], verbose=True)
        assert len(result) == 2
        captured = capsys.readouterr()
        assert "Ignored Directories" in captured.out
        assert "ignored" in captured.out

    def test_find_all_files_no_match_ignore(self, tmp_path, capsys):
        find_all_files(tmp_path, ["nonexistent"], verbose=True)
        assert "No directories matched" in capsys.readouterr().out

    def test_find_all_files_nonexistent(self):
        with pytest.raises(SystemExit):
            find_all_files(Path("/nonexistent"), [], False)


class TestFileProcessing:
    """Test processing individual files and parallel execution."""

    def test_process_one_file_no_changes(self, tmp_path):
        f = tmp_path / "test.cpp"
        f.write_text("int x = 1;")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=b"int x = 1;", returncode=0)
            path, changed, diff = process_one_file(f, "clang-format", check=True)
            assert not changed
            assert diff is None

    def test_process_one_file_in_place(self, tmp_path):
        f = tmp_path / "test.cpp"
        f.write_text("int x=1;")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            # Simulate file was changed by tool
            with patch(
                "pathlib.Path.read_bytes", side_effect=[b"int x=1;", b"int x = 1;"]
            ):
                path, changed, diff = process_one_file(f, "clang-format", check=False)
                assert changed

    def test_process_one_file_error(self, tmp_path, capsys):
        f = tmp_path / "test.cpp"
        with patch("subprocess.run", side_effect=Exception("Boom")):
            path, changed, diff = process_one_file(f, "clang-format", check=False)
            assert not changed
            assert "Error formatting" in capsys.readouterr().err

    def test_process_one_file_diff_logic(self, tmp_path):
        f = tmp_path / "test.cpp"
        f.write_text("old\n")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout=b"new\n", returncode=0)
            path, changed, diff = process_one_file(f, "clang-format", check=True)
            assert changed
            assert "+new" in diff
            assert "-old" in diff

    def test_process_files_parallel_success(self, tmp_path, capsys):
        root = tmp_path
        files = {root / "test.cpp": {"command": "clang-format"}}
        # Mock result showing changes needed with a diff
        mock_result = (str(root / "test.cpp"), True, "+new line\n-old line")
        with (
            patch(
                "concurrent.futures.ProcessPoolExecutor",
                concurrent.futures.ThreadPoolExecutor,
            ),
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.process_one_file",
                return_value=mock_result,
            ),
        ):
            with pytest.raises(SystemExit) as exc:
                process_files_parallel(files, root, 1, verbose=True, check=True)
            assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "Files Requiring Formatting" in captured.out
        assert "❌ test.cpp" in captured.out
        assert "+new line" in captured.out
        assert "-old line" in captured.out

    def test_process_files_parallel_check_success(self, tmp_path, capsys):
        root = tmp_path
        files = {root / "test.cpp": {"command": "clang-format"}}
        mock_result = (str(root / "test.cpp"), False, None)
        with (
            patch(
                "concurrent.futures.ProcessPoolExecutor",
                concurrent.futures.ThreadPoolExecutor,
            ),
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.process_one_file",
                return_value=mock_result,
            ),
        ):
            process_files_parallel(files, root, 1, verbose=False, check=True)
        assert "Check passed" in capsys.readouterr().out

    def test_process_files_parallel_format_done(self, tmp_path, capsys):
        root = tmp_path
        files = {root / "test.cpp": {"command": "clang-format"}}
        mock_result = (str(root / "test.cpp"), True, None)
        with (
            patch(
                "concurrent.futures.ProcessPoolExecutor",
                concurrent.futures.ThreadPoolExecutor,
            ),
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.process_one_file",
                return_value=mock_result,
            ),
        ):
            process_files_parallel(files, root, 1, verbose=True, check=False)
        captured = capsys.readouterr()
        assert "Files Found" in captured.out
        assert "Files Reformatted" in captured.out
        assert "✨ test.cpp" in captured.out
        assert "Done. 1 files were reformatted." in captured.out

    def test_process_files_parallel_exception(self, tmp_path, capsys):
        files = {tmp_path / "test.cpp": {"command": "clang-format"}}
        with patch("concurrent.futures.ProcessPoolExecutor") as mock_exec:
            mock_future = Mock()
            mock_future.result.side_effect = Exception("Boom")
            mock_exec.return_value.__enter__.return_value.submit.return_value = (
                mock_future
            )
            with patch("concurrent.futures.as_completed", return_value=[mock_future]):
                process_files_parallel(files, tmp_path, 1, False, False)
        assert "Boom" in capsys.readouterr().err


class TestFormatterCLI:
    """Test CLI and programmatic entry points."""

    def test_check_for_tools(self, capsys):
        with patch("shutil.which", return_value="/path/to/tool"):
            assert check_for_tools()
        with patch("shutil.which", return_value=None):
            assert not check_for_tools()
            assert "not found in PATH" in capsys.readouterr().out

    def test_main_success(self):
        with (
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.check_for_tools",
                return_value=True,
            ),
            patch("src.embedded_cereal_bowl.formatter.formatter.run_project_tasks"),
            patch("sys.argv", ["formatter", "src"]),
        ):
            main()

    def test_main_no_tools(self):
        with (
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.check_for_tools",
                return_value=False,
            ),
            patch("sys.argv", ["formatter"]),
            pytest.raises(SystemExit) as exc,
        ):
            main()
        assert exc.value.code == 1

    def test_main_keyboard_interrupt(self):
        with (
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.check_for_tools",
                return_value=True,
            ),
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.run_project_tasks",
                side_effect=KeyboardInterrupt,
            ),
            patch("sys.argv", ["formatter"]),
            pytest.raises(SystemExit) as exc,
        ):
            main()
        assert exc.value.code == 130

    def test_programmatic_interfaces(self):
        with (
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.check_for_tools",
                return_value=True,
            ),
            patch(
                "src.embedded_cereal_bowl.formatter.formatter.run_project_tasks"
            ) as mock_run,
        ):
            format_files("src")
            check_format("src")
            assert mock_run.call_count == 2

    def test_programmatic_no_tools(self):
        with patch(
            "src.embedded_cereal_bowl.formatter.formatter.check_for_tools",
            return_value=False,
        ):
            assert format_files() is None
            assert check_format() is None


def test_max_width_fallback():
    with patch("shutil.get_terminal_size", side_effect=OSError):
        import importlib

        import src.embedded_cereal_bowl.formatter.formatter as fmt

        importlib.reload(fmt)
        assert fmt.MAX_WIDTH == 80


def test_main_block():
    with (
        patch(
            "src.embedded_cereal_bowl.formatter.formatter.check_for_tools",
            return_value=True,
        ),
        patch("src.embedded_cereal_bowl.formatter.formatter.run_project_tasks"),
        patch("sys.argv", ["formatter"]),
    ):
        runpy.run_module(
            "src.embedded_cereal_bowl.formatter.formatter", run_name="__main__"
        )
