"""Tests for archive_logs utility."""

import zipfile
from pathlib import Path
from unittest.mock import patch

from src.embedded_cereal_bowl.archive_logs import cleanup_logs, main


def test_cleanup_logs_non_existent_dir(capsys):
    """Test cleanup_logs with a directory that doesn't exist."""
    cleanup_logs(Path("non_existent_dir_12345"))
    captured = capsys.readouterr()
    assert (
        "Error: The directory 'non_existent_dir_12345' was not found." in captured.out
    )


def test_cleanup_logs_success(tmp_path, capsys):
    """Test successful log archiving and deletion."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "test.log"
    log_file.write_text("test log content")

    # Run cleanup
    cleanup_logs(log_dir)

    # Verify log dir is gone
    assert not log_dir.exists()

    # Verify zip exists in parent (tmp_path)
    zips = list(tmp_path.glob("logs-*.zip"))
    assert len(zips) == 1

    # Verify zip content
    with zipfile.ZipFile(zips[0], "r") as zipf:
        assert "logs/test.log" in zipf.namelist()
        assert zipf.read("logs/test.log").decode() == "test log content"

    captured = capsys.readouterr()
    assert "Archive created successfully" in captured.out
    assert "Cleanup complete" in captured.out


def test_cleanup_logs_exception(tmp_path, capsys):
    """Test handling of exceptions during cleanup."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Mock zipfile to raise an exception
    with patch("zipfile.ZipFile", side_effect=Exception("Zip error")):
        cleanup_logs(log_dir)

    captured = capsys.readouterr()
    assert "An error occurred during the process: Zip error" in captured.out
    assert "The original logs folder was NOT deleted" in captured.out
    assert log_dir.exists()


def test_main_default(tmp_path):
    """Test main function with default arguments."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        with patch(
            "src.embedded_cereal_bowl.archive_logs.cleanup_logs"
        ) as mock_cleanup:
            with patch("sys.argv", ["archive_logs"]):
                main()
                mock_cleanup.assert_called_once_with(logs_dir)


def test_main_custom_dir(tmp_path):
    """Test main function with custom directory argument."""
    custom_dir = tmp_path / "custom_logs"
    custom_dir.mkdir()

    with patch("pathlib.Path.cwd", return_value=tmp_path):
        with patch(
            "src.embedded_cereal_bowl.archive_logs.cleanup_logs"
        ) as mock_cleanup:
            with patch("sys.argv", ["archive_logs", "custom_logs"]):
                main()
                mock_cleanup.assert_called_once_with(custom_dir)


def test_archive_logs_main_block():
    """Test archive_logs.py __main__ block."""
    import runpy

    with (
        patch("argparse.ArgumentParser.parse_args", side_effect=SystemExit(0)),
        patch("sys.argv", ["archive_logs.py"]),
        patch("builtins.print"),
    ):
        try:
            runpy.run_module(
                "src.embedded_cereal_bowl.archive_logs", run_name="__main__"
            )
        except SystemExit:
            pass
