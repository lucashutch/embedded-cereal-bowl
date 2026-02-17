"""Tests for the timestamp conversion module."""

import runpy
from datetime import datetime
from unittest.mock import patch

import pytest

from src.embedded_cereal_bowl.timestamp.timestamp import main, parse_and_convert_time


class TestParseAndConvertTime:
    """Test cases for the parse_and_convert_time function."""

    def test_unix_timestamp_seconds(self):
        ts = 1672531200.0  # 2023-01-01 00:00:00 UTC
        utc_str, _, utc_ts = parse_and_convert_time(str(ts))
        assert utc_str == "2023-01-01T00:00:00.000Z"
        assert utc_ts == ts

    def test_milliseconds_timestamp_large(self):
        ms_ts = 1672531200123
        utc_str, _, utc_ts = parse_and_convert_time(str(ms_ts))
        assert utc_str == "2023-01-01T00:00:00.123Z"
        assert utc_ts == 1672531200.123

    def test_iso8601_string(self):
        iso_str = "2023-01-01T12:30:45.567Z"
        utc_str, _, utc_ts = parse_and_convert_time(iso_str)
        assert utc_str == iso_str
        assert isinstance(utc_ts, float)

    def test_iso8601_string_no_offset(self):
        iso_str = "2023-01-01T12:30:45.567"
        utc_str, _, utc_ts = parse_and_convert_time(iso_str)
        assert utc_str == "2023-01-01T12:30:45.567Z"

    def test_invalid_input(self):
        with pytest.raises(ValueError, match="is neither a valid Unix timestamp"):
            parse_and_convert_time("invalid")

    def test_local_timezone(self):
        ts = "1672531200.123"
        _, local_str, _ = parse_and_convert_time(ts)
        assert "T" in local_str
        assert datetime.fromisoformat(local_str).tzinfo is not None


class TestTimestampCLI:
    """Test the CLI interface for timestamp conversion."""

    def test_main_success(self, capsys):
        with patch("sys.argv", ["timestamp", "1672531200"]):
            main()
        assert "2023-01-01" in capsys.readouterr().out

    def test_main_error(self, capsys):
        with patch("sys.argv", ["timestamp", "invalid"]), pytest.raises(SystemExit):
            main()
        assert "Error:" in capsys.readouterr().out


def test_main_block():
    with (
        patch(
            "src.embedded_cereal_bowl.timestamp.timestamp.parse_and_convert_time",
            return_value=("", "", 0.0),
        ),
        patch("sys.argv", ["timestamp", "0"]),
        patch("builtins.print"),
    ):
        runpy.run_module(
            "src.embedded_cereal_bowl.timestamp.timestamp", run_name="__main__"
        )
