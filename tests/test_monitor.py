"""Test configuration and utilities."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import serial

# Add src directory to path for testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.embedded_cereal_bowl.monitor.monitor import (
    add_time_to_line,
    clear_terminal,
    create_replacement_lambda,
    get_serial_port_name,
    get_serial_prefix,
    parse_arguments,
    run_serial_printing_with_logs,
    send_serial_data,
    wait_with_spinner,
)


class TestParseArguments:
    """Test cases for parse_arguments function."""

    def test_parse_arguments_defaults(self):
        """Test parsing with default arguments."""
        with patch("sys.argv", ["monitor"]):
            args = parse_arguments()

            assert args.port == "ACM0" if os.name != "nt" else "COM3"
            assert args.baud == 115200
            assert args.log is False
            assert args.log_file == ""
            assert args.log_directory.endswith("logs")
            assert args.clear is False
            assert args.print_time == "off"
            assert args.highlight is None
            assert args.send is False

    def test_parse_arguments_custom_values(self):
        """Test parsing with custom arguments."""
        test_args = [
            "monitor",
            "-p",
            "USB0",
            "-b",
            "9600",
            "-l",
            "--log-file",
            "test",
            "--log-directory",
            "/tmp/logs",
            "-c",
            "--print_time",
            "epoch",
            "--highlight",
            "error,warning",
            "--send",
        ]

        with patch("sys.argv", test_args):
            args = parse_arguments()

            assert args.port == "USB0"
            assert args.baud == 9600
            assert args.log is True
            assert args.log_file == "test"
            assert args.log_directory == "/tmp/logs"
            assert args.clear is True
            assert args.print_time == "epoch"
            assert args.highlight == "error,warning"
            assert args.send is True

    def test_parse_arguments_print_time_choices(self):
        """Test valid print_time choices."""
        choices = ["off", "epoch", "ms", "dt"]

        for choice in choices:
            with patch("sys.argv", ["monitor", "--print_time", choice]):
                args = parse_arguments()
                assert args.print_time == choice


class TestGetSerialPrefix:
    """Test cases for get_serial_prefix function."""

    def test_get_serial_prefix_nt(self):
        """Test serial prefix on Windows."""
        with patch("os.name", "nt"):
            prefix = get_serial_prefix()
            assert prefix == ""

    def test_get_serial_prefix_unix(self):
        """Test serial prefix on Unix systems."""
        with patch("os.name", "posix"):
            prefix = get_serial_prefix()
            assert prefix == "/dev/tty"


class TestGetSerialPortName:
    """Test cases for get_serial_port_name function."""

    def test_get_serial_port_name_nt(self):
        """Test port name construction on Windows."""
        with patch("os.name", "nt"):
            assert get_serial_port_name("COM3") == "COM3"
            assert get_serial_port_name("COM10") == "COM10"

    def test_get_serial_port_name_unix_short(self):
        """Test port name construction on Unix with short name."""
        with patch("os.name", "posix"):
            assert get_serial_port_name("ACM0") == "/dev/ttyACM0"
            assert get_serial_port_name("USB0") == "/dev/ttyUSB0"

    def test_get_serial_port_name_unix_tty(self):
        """Test port name construction on Unix with tty prefix."""
        with patch("os.name", "posix"):
            assert get_serial_port_name("ttyACM0") == "/dev/ttyACM0"
            assert get_serial_port_name("ttyUSB0") == "/dev/ttyUSB0"

    def test_get_serial_port_name_unix_full(self):
        """Test port name construction on Unix with full path."""
        with patch("os.name", "posix"):
            assert get_serial_port_name("/dev/ttyACM0") == "/dev/ttyACM0"
            assert get_serial_port_name("/dev/rfcomm0") == "/dev/rfcomm0"
            assert get_serial_port_name("/dev/pts/1") == "/dev/pts/1"


class TestClearTerminal:
    """Test cases for clear_terminal function."""

    def test_clear_terminal_nt(self):
        """Test terminal clearing on Windows."""
        with patch("os.name", "nt"), patch("os.system") as mock_system:
            clear_terminal()
            mock_system.assert_called_once_with("cls")

    def test_clear_terminal_unix(self):
        """Test terminal clearing on Unix."""
        with patch("os.name", "posix"), patch("os.system") as mock_system:
            clear_terminal()
            mock_system.assert_called_once_with("clear")


class TestAddTimeToLine:
    """Test cases for add_time_to_line function."""

    @patch("src.embedded_cereal_bowl.monitor.monitor.datetime")
    def test_add_time_to_line_off(self, mock_datetime):
        """Test adding timestamp with 'off' mode."""
        result = add_time_to_line("off")
        assert result == ""
        mock_datetime.assert_not_called()

    @patch("src.embedded_cereal_bowl.monitor.monitor.datetime")
    def test_add_time_to_line_epoch(self, mock_datetime):
        """Test adding timestamp with 'epoch' mode."""
        # Mock current time
        mock_now = Mock()
        mock_now.timestamp.return_value = 1672531200.123
        mock_datetime.now.return_value = mock_now
        mock_datetime.now.return_value.replace.return_value = mock_now

        result = add_time_to_line("epoch")
        assert result == "1672531200.123 "

    @patch("src.embedded_cereal_bowl.monitor.monitor.datetime")
    def test_add_time_to_line_ms(self, mock_datetime):
        """Test adding timestamp with 'ms' mode."""
        # Mock current time
        mock_now = Mock()
        mock_now.timestamp.return_value = 1672531200.123
        mock_datetime.now.return_value = mock_now

        result = add_time_to_line("ms")
        assert result == "1672531200123 "

    @patch("src.embedded_cereal_bowl.monitor.monitor.datetime")
    def test_add_time_to_line_dt(self, mock_datetime):
        """Test adding timestamp with 'dt' mode."""
        # Mock current time
        mock_now = Mock()
        mock_now.replace.return_value.isoformat.return_value = "2023-01-01 10:00:00.123"
        mock_datetime.now.return_value = mock_now

        result = add_time_to_line("dt")
        assert result == "2023-01-01 10:00:00.123 "

    def test_add_time_to_line_invalid_mode(self):
        """Test adding timestamp with invalid mode."""
        result = add_time_to_line("invalid")
        assert result == ""


class TestCreateReplacementLambda:
    """Test cases for create_replacement_lambda function."""

    def test_create_replacement_lambda_basic(self):
        """Test basic replacement lambda creation."""
        line_state = "this is a test line with error"

        with patch(
            "src.embedded_cereal_bowl.monitor.monitor.colour_str"
        ) as mock_colour:
            mock_coloured = Mock()
            mock_coloured.back_green.return_value = mock_coloured
            mock_coloured.black.return_value = mock_coloured
            mock_colour.return_value = mock_coloured
            mock_coloured.__str__ = Mock(return_value="highlighted_error")

            lambda_func = create_replacement_lambda(line_state)

            # Create a mock match object
            mock_match = Mock()
            mock_match.group.return_value = "error"
            mock_match.start.return_value = 22
            mock_match.end.return_value = 27

            result = lambda_func(mock_match)

            mock_colour.assert_called_once_with("error")
            mock_coloured.back_green.assert_called_once()
            mock_coloured.black.assert_called_once()

    def test_create_replacement_lambda_with_ansi_codes(self):
        """Test replacement lambda with ANSI codes in the line."""
        line_state = "normal text \x1b[31mred text\x1b[0m error"

        with patch(
            "src.embedded_cereal_bowl.monitor.monitor.colour_str"
        ) as mock_colour:
            mock_coloured = Mock()
            mock_coloured.back_green.return_value = mock_coloured
            mock_coloured.black.return_value = mock_coloured
            mock_colour.return_value = mock_coloured
            mock_coloured.__str__ = Mock(return_value="highlighted_error")

            lambda_func = create_replacement_lambda(line_state)

            mock_match = Mock()
            mock_match.group.return_value = "error"
            mock_match.start.return_value = len("normal text \x1b[31mred text\x1b[0m ")
            mock_match.end.return_value = len(
                "normal text \x1b[31mred text\x1b[0m error"
            )

            result = lambda_func(mock_match)

            # Should find preceding codes and apply them after highlighting
            mock_colour.assert_called_once_with("error")


class TestSendSerialData:
    """Test cases for send_serial_data function."""

    @patch("src.embedded_cereal_bowl.monitor.monitor.add_time_to_line")
    def test_send_serial_data_no_file(self):
        """Test sending data without logging file."""
        mock_ser = Mock()
        mock_add_time = Mock(return_value="timestamp ")

        with patch(
            "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line", mock_add_time
        ):
            with patch("builtins.print") as mock_print:
                result = send_serial_data(mock_ser, "test data", "epoch", None)

                assert result is True
                mock_print.assert_called_once_with("timestamp test data\n", end="")
            mock_file.write.assert_called_once_with("timestamp test data\n")

    @patch("src.embedded_cereal_bowl.monitor.monitor.add_time_to_line")
    def test_send_serial_data_with_newline(self, mock_add_time):
        """Test sending data that already has a newline."""
        mock_ser = Mock()
        mock_file = Mock()
        mock_add_time.return_value = "timestamp test data\n"

        result = send_serial_data(mock_ser, "test data\n", "epoch", mock_file)

        assert result is True
        # Should not add another newline
        mock_ser.write.assert_called_once_with(b"test data\n")

    @patch("src.embedded_cereal_bowl.monitor.monitor.colour_str")
    @patch("src.embedded_cereal_bowl.monitor.monitor.add_time_to_line")
    def test_send_serial_data_serial_exception(self, mock_add_time, mock_colour):
        """Test handling of serial exception."""
        mock_ser = Mock()
        mock_ser.write.side_effect = serial.SerialException("Serial error")
        mock_file = Mock()
        mock_add_time.return_value = "timestamp test data\n"
        mock_colour.return_value = Mock()
        mock_colour.return_value.red.return_value = "colored error"

        with patch("builtins.print") as mock_print:
            result = send_serial_data(mock_ser, "test data", "epoch", mock_file)

            assert result is False
            mock_print.assert_called()

    def test_send_serial_data_no_file(self):
        """Test sending data without logging file."""
        mock_ser = Mock()
        mock_add_time = Mock(return_value="timestamp ")

        with (
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line",
                mock_add_time,
            ),
            patch("builtins.print") as mock_print,
        ):
            result = send_serial_data(mock_ser, "test data", "epoch", None)

            assert result is True
            mock_print.assert_called_once_with("timestamp test data\n", end="")


class TestWaitWithSpinner:
    """Test cases for wait_with_spinner function."""

    @patch("sys.stdout.write")
    @patch("sys.stdout.flush")
    @patch("src.embedded_cereal_bowl.monitor.monitor.colour_str")
    def test_wait_with_spinner_basic(self, mock_colour, mock_flush, mock_write):
        """Test basic spinner functionality."""
        mock_colour.return_value = Mock()
        mock_colour.return_value.dim.return_value.__str__ = Mock(
            return_value="spinner text"
        )

        result = wait_with_spinner("/dev/ttyUSB0", 0)

        assert result == 1
        mock_colour.assert_called_once()
        mock_write.assert_called_once_with("\rspinner text")
        mock_flush.assert_called_once()

    @patch("sys.stdout.write")
    @patch("sys.stdout.flush")
    @patch("src.embedded_cereal_bowl.monitor.monitor.colour_str")
    def test_wait_with_spinner_cycling(self, mock_colour, mock_flush, mock_write):
        """Test spinner cycling through different states."""
        mock_colour.return_value = Mock()
        mock_colour.return_value.dim.return_value.__str__ = Mock(
            return_value="spinner text"
        )

        # Test multiple cycles
        result1 = wait_with_spinner("/dev/ttyUSB0", 0)
        result2 = wait_with_spinner("/dev/ttyUSB0", 1)
        result3 = wait_with_spinner("/dev/ttyUSB0", 2)
        result4 = wait_with_spinner("/dev/ttyUSB0", 3)
        result5 = wait_with_spinner("/dev/ttyUSB0", 4)

        assert result1 == 1
        assert result2 == 2
        assert result3 == 3
        assert result4 == 4
        assert result5 == 5

        # Should have been called 5 times
        assert mock_colour.call_count == 5
        assert mock_write.call_count == 5
        assert mock_flush.call_count == 5


class TestRunSerialPrintingWithLogs:
    """Test cases for run_serial_printing_with_logs function."""

    @patch("src.embedded_cereal_bowl.monitor.monitor.run_serial_printing")
    @patch("src.embedded_cereal_bowl.monitor.monitor.datetime")
    @patch("os.path.isdir")
    @patch("os.mkdir")
    def test_run_serial_printing_with_logs_new_directory(
        self, mock_mkdir, mock_isdir, mock_datetime, mock_run
    ):
        """Test logging with new directory creation."""
        mock_isdir.return_value = False
        mock_datetime.now.return_value.strftime.return_value = "2023.01.01_12.00.00"

        with patch("builtins.open", mock_open()) as mock_file:
            run_serial_printing_with_logs(
                "/dev/ttyUSB0", 115200, "test", "/tmp/logs", "epoch", None, False
            )

            mock_isdir.assert_called_once_with("/tmp/logs")
            mock_mkdir.assert_called_once_with("/tmp/logs")
            mock_file.assert_called_once_with(
                "/tmp/logs/2023.01.01_12.00.00_test.txt", "a+", buffering=1
            )
            mock_run.assert_called_once()

    @patch("src.embedded_cereal_bowl.monitor.monitor.run_serial_printing")
    @patch("src.embedded_cereal_bowl.monitor.monitor.datetime")
    @patch("os.path.isdir")
    @patch("os.mkdir")
    def test_run_serial_printing_with_logs_existing_directory(
        self, mock_mkdir, mock_isdir, mock_datetime, mock_run
    ):
        """Test logging with existing directory."""
        mock_isdir.return_value = True
        mock_datetime.now.return_value.strftime.return_value = "2023.01.01_12.00.00"

        with patch("builtins.open", mock_open()) as mock_file:
            run_serial_printing_with_logs(
                "/dev/ttyUSB0", 115200, "test", "/tmp/logs", "epoch", None, False
            )

            mock_isdir.assert_called_once_with("/tmp/logs")
            mock_mkdir.assert_not_called()  # Directory already exists
            mock_file.assert_called_once_with(
                "/tmp/logs/2023.01.01_12.00.00_test.txt", "a+", buffering=1
            )
            mock_run.assert_called_once()
