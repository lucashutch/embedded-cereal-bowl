"""Tests for the CLI module."""

import runpy
from unittest.mock import Mock, patch

import pytest

from src.embedded_cereal_bowl.cli import (
    main_check_crlf,
    main_cli,
    main_formatter,
    main_monitor,
    main_timestamp,
)


class TestCLIEntryPoints:
    """Test individual CLI entry point functions."""

    @patch("src.embedded_cereal_bowl.monitor.monitor.parse_arguments")
    @patch("src.embedded_cereal_bowl.monitor.monitor.run_serial_printing")
    def test_main_monitor(self, mock_run, mock_parse):
        mock_args = Mock(
            port="ACM0",
            baud=115200,
            log=False,
            log_file="",
            log_directory="/logs",
            clear=False,
            print_time=None,
            highlight=None,
            send=False,
        )
        mock_parse.return_value = mock_args
        with patch("sys.argv", ["monitor"]), patch("builtins.print"):
            main_monitor()
        mock_run.assert_called_once()

    @patch("src.embedded_cereal_bowl.timestamp.timestamp.parse_and_convert_time")
    def test_main_timestamp_success(self, mock_parse):
        mock_parse.return_value = ("2023-01-01T12:30:45.567Z", "local", 1672573845.567)
        with (
            patch("sys.argv", ["timestamp", "1672573845.567"]),
            patch("builtins.print"),
        ):
            main_timestamp()
        mock_parse.assert_called_once_with("1672573845.567")

    def test_main_formatter(self):
        with (
            patch("sys.argv", ["format-code", "/test/path"]),
            pytest.raises(SystemExit),
        ):
            main_formatter()

    def test_main_check_crlf(self):
        with patch("sys.argv", ["check-crlf"]), patch("sys.exit") as mock_exit:
            try:
                main_check_crlf()
            except SystemExit:
                pass
            mock_exit.assert_called()


class TestCLIDispatcher:
    """Test the main CLI tool dispatcher."""

    def test_cli_dispatch_monitor(self):
        with (
            patch("sys.argv", ["cli.py", "monitor"]),
            patch("src.embedded_cereal_bowl.cli.main_monitor") as mock_tool,
        ):
            main_cli()
            mock_tool.assert_called_once()

    def test_cli_dispatch_timestamp(self):
        with (
            patch("sys.argv", ["cli.py", "timestamp"]),
            patch("src.embedded_cereal_bowl.cli.main_timestamp") as mock_tool,
        ):
            main_cli()
            mock_tool.assert_called_once()

    def test_cli_dispatch_check_crlf(self):
        with (
            patch("sys.argv", ["cli.py", "check-crlf"]),
            patch("src.embedded_cereal_bowl.cli.main_check_crlf") as mock_tool,
        ):
            main_cli()
            mock_tool.assert_called_once()

    def test_cli_dispatch_formatter(self):
        with (
            patch("sys.argv", ["cli.py", "format-code"]),
            patch("src.embedded_cereal_bowl.cli.main_formatter") as mock_tool,
        ):
            main_cli()
            mock_tool.assert_called_once()

    def test_cli_dispatch_invalid(self, capsys):
        with patch("sys.argv", ["cli.py", "invalid"]), pytest.raises(SystemExit) as exc:
            main_cli()
        assert exc.value.code == 1
        assert "Usage:" in capsys.readouterr().out

    def test_cli_dispatch_no_args(self, capsys):
        with patch("sys.argv", ["cli.py"]), pytest.raises(SystemExit) as exc:
            main_cli()
        assert exc.value.code == 1
        assert "Usage:" in capsys.readouterr().out


def test_cli_main_block():
    """Test cli.py __main__ block."""
    with (
        patch("src.embedded_cereal_bowl.monitor.main") as mock_monitor,
        patch("sys.argv", ["cli.py", "monitor"]),
    ):
        runpy.run_module("src.embedded_cereal_bowl.cli", run_name="__main__")
        mock_monitor.assert_called_once()
