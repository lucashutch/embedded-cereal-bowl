"""Tests for the serial monitor module."""

import sys
import threading
from unittest.mock import Mock, mock_open, patch

import pytest
import serial

from src.embedded_cereal_bowl.monitor.monitor import (
    ASNI_ESCAPE_PATTERN,
    add_time_to_line,
    clear_terminal,
    create_replacement_lambda,
    get_serial_port_name,
    get_serial_prefix,
    handle_user_input,
    main,
    parse_arguments,
    run_serial_printing,
    run_serial_printing_with_logs,
    serial_loop,
    wait_with_spinner,
)


class TestMonitorArguments:
    """Test argument parsing and port name resolution."""

    def test_parse_arguments_defaults(self):
        with patch("sys.argv", ["monitor"]):
            args = parse_arguments()
            assert args.baud == 115200
            assert args.log is False

    @patch("sys.argv", ["monitor", "--print_time", "invalid choice"])
    def test_invalid_print_time_choice(self):
        with pytest.raises(SystemExit):
            parse_arguments()

    def test_get_serial_prefix(self):
        with patch("os.name", "nt"):
            assert get_serial_prefix() == ""
        with patch("os.name", "posix"):
            assert get_serial_prefix() == "/dev/tty"

    def test_get_serial_port_name(self):
        with patch("os.name", "posix"):
            assert get_serial_port_name("ACM0") == "/dev/ttyACM0"
            assert get_serial_port_name("/dev/custom") == "/dev/custom"
            assert get_serial_port_name("ttyUSB0") == "/dev/ttyUSB0"
            assert get_serial_port_name("USB0") == "/dev/ttyUSB0"
        with patch("os.name", "nt"):
            assert get_serial_port_name("COM3") == "COM3"


class TestMonitorUtilities:
    """Test utility functions like terminal clearing and timestamping."""

    def test_clear_terminal(self):
        with patch("os.name", "nt"), patch("os.system") as mock_sys:
            clear_terminal()
            mock_sys.assert_called_with("cls")
        with patch("os.name", "posix"), patch("os.system") as mock_sys:
            clear_terminal()
            mock_sys.assert_called_with("clear")

    def test_add_time_to_line(self):
        assert add_time_to_line(None) == ""
        with patch("src.embedded_cereal_bowl.monitor.monitor.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.timestamp.return_value = 1000.0
            mock_dt.now.return_value = mock_now
            mock_dt.now.return_value.replace.return_value.isoformat.return_value = (
                "2023-01-01 10:00:00.000"
            )

            assert "1000.000" in add_time_to_line("epoch")
            assert "1000000" in add_time_to_line("ms")
            assert "2023-01-01" in add_time_to_line("dt")
        assert add_time_to_line("invalid") == ""

    def test_ansi_escape_pattern(self):
        assert ASNI_ESCAPE_PATTERN.search("\x1b[31m")
        assert not ASNI_ESCAPE_PATTERN.search("plain")

    def test_create_replacement_lambda(self):
        line_state = "normal \x1b[31mred\x1b[0m error"
        with patch(
            "src.embedded_cereal_bowl.monitor.monitor.colour_str"
        ) as mock_colour:
            mock_chain = Mock()
            mock_chain.back_green.return_value = mock_chain
            mock_chain.black.return_value = mock_chain
            mock_chain.__str__ = Mock(return_value="MATCH")
            mock_colour.return_value = mock_chain

            callback = create_replacement_lambda(line_state)
            mock_match = Mock()
            mock_match.group.return_value = "error"
            mock_match.start.return_value = len("normal \x1b[31mred\x1b[0m ")
            result = callback(mock_match)
            assert result is not None

    def test_create_replacement_lambda_no_reset(self):
        line_state = "\x1b[31mred error"
        with patch(
            "src.embedded_cereal_bowl.monitor.monitor.colour_str"
        ) as mock_colour:
            mock_chain = Mock()
            mock_chain.back_green.return_value = mock_chain
            mock_chain.black.return_value = mock_chain
            mock_chain.__str__ = Mock(return_value="MATCH")
            mock_colour.return_value = mock_chain

            callback = create_replacement_lambda(line_state)
            mock_match = Mock()
            mock_match.group.return_value = "error"
            mock_match.start.return_value = len("\x1b[31mred ")
            result = callback(mock_match)
            assert "\x1b[31m" in result


class TestMonitorLogic:
    """Test the core monitor logic and loops."""

    def test_wait_with_spinner(self):
        with patch("sys.stdout.write"), patch("sys.stdout.flush"):
            assert wait_with_spinner("port", 0) == 1
            assert wait_with_spinner("port", 3) == 4

    @patch("src.embedded_cereal_bowl.monitor.monitor.run_serial_printing")
    @patch("os.mkdir")
    @patch("os.path.isdir", return_value=False)
    def test_run_serial_printing_with_logs(self, mock_isdir, mock_mkdir, mock_run):
        with patch("builtins.open", mock_open()):
            run_serial_printing_with_logs("p", 115200, "f", "d", "epoch")
            mock_mkdir.assert_called_once_with("d")
            mock_run.assert_called_once()

    def test_serial_loop_basic(self):
        mock_ser = Mock()
        # Test empty line then real line then stop
        mock_ser.readline.side_effect = [b"", b"line1\n", KeyboardInterrupt()]
        with (
            patch("builtins.print"),
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line",
                return_value="",
            ),
        ):
            try:
                serial_loop(mock_ser, None, None)
            except KeyboardInterrupt:
                pass
        assert mock_ser.readline.call_count >= 2

    def test_serial_loop_with_highlighting(self):
        mock_ser = Mock()
        mock_ser.readline.side_effect = [b"error\n", KeyboardInterrupt()]
        with (
            patch("builtins.print"),
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line",
                return_value="",
            ),
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.create_replacement_lambda",
                return_value=lambda m: "!",
            ),
        ):
            try:
                serial_loop(mock_ser, None, None, highlight_words=["error", ""])
            except KeyboardInterrupt:
                pass

    def test_serial_loop_with_logging(self):
        mock_ser = Mock()
        mock_ser.readline.side_effect = [b"data\n", KeyboardInterrupt()]
        mock_file = Mock()
        with (
            patch("builtins.print"),
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line",
                return_value="",
            ),
        ):
            try:
                serial_loop(mock_ser, None, mock_file)
            except KeyboardInterrupt:
                pass
        mock_file.write.assert_called()

    def test_serial_loop_finally_cleanup(self):
        mock_ser = Mock()
        mock_ser.readline.side_effect = [b"line\n", KeyboardInterrupt()]
        with patch("threading.Thread") as mock_thread_class:
            mock_thread_instance = Mock()
            mock_thread_instance.is_alive.return_value = True
            mock_thread_class.return_value = mock_thread_instance
            with (
                patch("builtins.print"),
                patch(
                    "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line",
                    return_value="",
                ),
            ):
                try:
                    serial_loop(mock_ser, None, None, enable_send=True)
                except KeyboardInterrupt:
                    pass
            mock_thread_instance.join.assert_called_once()

    def test_handle_user_input_normal(self):
        mock_ser = Mock()
        stop_event = threading.Event()
        with (
            patch("select.select", return_value=([sys.stdin], [], [])),
            patch("sys.stdin.readline", side_effect=["cmd\n", KeyboardInterrupt()]),
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.send_serial_data"
            ) as mock_send,
        ):
            try:
                handle_user_input(mock_ser, None, None, stop_event)
            except KeyboardInterrupt:
                pass
            mock_send.assert_called()

    def test_handle_user_input_errors(self, capsys):
        mock_ser = Mock()
        stop_event = threading.Event()
        with patch("select.select", side_effect=OSError):
            handle_user_input(mock_ser, None, None, stop_event)
        with (
            patch("select.select", return_value=([sys.stdin], [], [])),
            patch("sys.stdin.readline", side_effect=Exception("Read error")),
        ):
            handle_user_input(mock_ser, None, None, stop_event)
            assert "Input error" in capsys.readouterr().out

    def test_send_serial_data_basic(self):
        mock_ser = Mock()
        mock_file = Mock()
        with (
            patch("builtins.print"),
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line",
                return_value="",
            ),
        ):
            from src.embedded_cereal_bowl.monitor.monitor import send_serial_data

            assert send_serial_data(mock_ser, "test", None, mock_file)
            mock_ser.write.assert_called_with(b"test\n")
            mock_file.write.assert_called_once()

    def test_send_serial_data_error(self, capsys):
        mock_ser = Mock()
        mock_ser.write.side_effect = serial.SerialException("Boom")
        with patch(
            "src.embedded_cereal_bowl.monitor.monitor.add_time_to_line",
            return_value="",
        ):
            from src.embedded_cereal_bowl.monitor.monitor import send_serial_data

            assert not send_serial_data(mock_ser, "test", None, None)
            assert "Send error" in capsys.readouterr().out


class TestMonitorIntegration:
    """Integration-style tests for the monitor."""

    @patch("time.sleep")
    @patch("serial.Serial")
    def test_run_serial_printing_success(self, mock_serial, mock_sleep):
        mock_ser = Mock()
        mock_serial.return_value.__enter__.return_value = mock_ser
        with (
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.serial_loop",
                side_effect=KeyboardInterrupt,
            ),
            patch("builtins.print"),
            pytest.raises(SystemExit),
        ):
            run_serial_printing("port", 115200)

    def test_run_serial_printing_exception(self):
        with (
            patch("time.sleep"),
            patch("serial.Serial") as mock_serial,
            patch(
                "src.embedded_cereal_bowl.monitor.monitor.wait_with_spinner"
            ) as mock_spin,
        ):
            mock_serial.side_effect = [
                serial.SerialException("Boom"),
                KeyboardInterrupt(),
            ]
            with patch("builtins.print"), pytest.raises(SystemExit):
                run_serial_printing("port", 115200)
            mock_spin.assert_called_once()

    @patch("src.embedded_cereal_bowl.monitor.monitor.colour_str")
    def test_run_serial_printing_keyboard_interrupt(self, mock_colour):
        mock_color_obj = Mock()
        mock_color_obj.dim.return_value = mock_color_obj
        mock_color_obj.green.return_value = mock_color_obj
        mock_colour.return_value = mock_color_obj

        with patch(
            "src.embedded_cereal_bowl.monitor.monitor.serial.Serial"
        ) as mock_serial:
            mock_serial.side_effect = KeyboardInterrupt()
            with patch("builtins.print"), pytest.raises(SystemExit) as exc:
                run_serial_printing("port", 115200)
            assert exc.value.code == 0


def test_monitor_main():
    with (
        patch("src.embedded_cereal_bowl.monitor.monitor.parse_arguments") as mock_parse,
        patch("src.embedded_cereal_bowl.monitor.monitor.run_serial_printing"),
        patch(
            "src.embedded_cereal_bowl.monitor.monitor.run_serial_printing_with_logs"
        ) as mock_run_logs,
        patch("builtins.print"),
    ):
        mock_parse.return_value = Mock(
            clear=False,
            highlight=None,
            log=False,
            send=False,
            port="p",
            baud=115200,
            print_time=None,
        )
        main()

        mock_parse.return_value = Mock(
            clear=True,
            highlight="[a,b]",
            log=True,
            send=True,
            port="p",
            baud=115200,
            print_time="epoch",
            log_file="lf",
            log_directory="ld",
        )
        with patch("src.embedded_cereal_bowl.monitor.monitor.clear_terminal"):
            main()
            mock_run_logs.assert_called_once()


def test_monitor_main_block():
    import runpy

    with (
        patch("argparse.ArgumentParser.parse_args", side_effect=SystemExit(0)),
        patch("sys.argv", ["monitor.py"]),
    ):
        try:
            runpy.run_module(
                "src.embedded_cereal_bowl.monitor.monitor", run_name="__main__"
            )
        except SystemExit:
            pass
