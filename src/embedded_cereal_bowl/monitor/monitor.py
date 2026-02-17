#! /usr/bin/env python3

import argparse
import os
import select
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import regex as re
import serial

from .. import __version__
from ..utils.color_utils import colour_str

ASNI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "A versatile serial monitor with read/write capabilities, "
            "logging, and auto-reconnect."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        default="COM3" if os.name == "nt" else "ACM0",
        help="Specify the serial port to connect to, eg ACM0, USB0, COM3",
    )
    parser.add_argument(
        "-b",
        "--baud",
        type=int,
        default=115200,
        help="Baud rate to set the serial port to",
    )
    parser.add_argument(
        "-l", "--log", action="store_true", help="save serial port data to log file"
    )
    parser.add_argument(
        "-lf",
        "--log-file",
        type=str,
        default="",
        help="filename used to save log files. Will appear as date_time_<filename>.txt",
    )
    parser.add_argument(
        "-ld",
        "--log-directory",
        type=str,
        help="Folder to save logging file. Default is script directory",
        default=os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs"),
    )
    parser.add_argument(
        "-c", "--clear", action="store_true", help="Clear terminal before printing"
    )
    parser.add_argument(
        "-t",
        "--print_time",
        type=str,
        default="off",
        choices=["off", "epoch", "ms", "dt"],
        help="Print system time on each log line:\n"
        "  off   - No timestamp\n"
        "  epoch - Unix timestamp with ms (e.g., 1672531200.123)\n"
        "  ms    - Milliseconds since epoch\n"
        "  dt    - Human-readable datetime (e.g., 2023-01-01 10:00:00.123)",
    )
    parser.add_argument(
        "--highlight",
        type=str,
        default=None,
        help="Comma-separated list of words to highlight (case-insensitive).\n"
        "Example: --highlight=error,warning,fail",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Enable interactive sending mode - type commands to send to serial device",
    )
    return parser.parse_args()


def get_serial_prefix() -> str:
    if os.name == "nt":
        return ""
    return "/dev/tty"


def get_serial_port_name(port_arg: str) -> str:
    """Construct the full serial port name based on user input and OS."""
    if os.name == "nt":
        return port_arg

    if port_arg.startswith("/"):
        return port_arg

    if port_arg.startswith("tty"):
        return f"/dev/{port_arg}"

    return f"{get_serial_prefix()}{port_arg}"


def clear_terminal() -> None:
    # clear screen
    if os.name == "nt":
        os.system("cls")  # nosec B605 B607
    else:
        os.system("clear")  # nosec B605 B607


def run_serial_printing_with_logs(
    serial_port_name: str,
    baud: int,
    log_file: str,
    log_directory: str,
    print_time: str,
    highlight_words: list[str] | None = None,
    enable_send: bool = False,
) -> None:
    filename = f"{datetime.now().strftime('%Y.%m.%d_%H.%M.%S')}_{log_file}.txt"
    if not os.path.isdir(log_directory):
        os.mkdir(log_directory)

    logging_file = os.path.join(log_directory, filename)
    print(f"Logging to: {logging_file}")

    with open(logging_file, "a+", buffering=1) as file:
        run_serial_printing(
            serial_port_name, baud, print_time, file, highlight_words, enable_send
        )


def add_time_to_line(print_time: str) -> str:
    now_utc = datetime.now(UTC)
    if "epoch" in print_time:
        return f"{now_utc.timestamp():.3f} "
    elif "ms" in print_time:
        return f"{now_utc.timestamp() * 1000:.0f} "
    elif "dt" in print_time:
        formatted_dt = now_utc.replace(tzinfo=None).isoformat(
            sep=" ", timespec="milliseconds"
        )
        return f"{formatted_dt} "
    return ""


def create_replacement_lambda(
    current_line_state: str,
) -> Callable[[re.Match[str]], str]:
    def find_and_replace(match: re.Match[str]) -> str:
        # Part of the line before the current match
        pre_match_str = current_line_state[: match.start()]
        # Find all ANSI codes before the match
        preceding_codes = ASNI_ESCAPE_PATTERN.findall(pre_match_str)
        # Determine the last active color state
        last_state = ""
        if preceding_codes:
            # Find the position of the last "reset" code
            last_reset_index = -1
            try:
                last_reset_index = max(
                    i for i, code in enumerate(preceding_codes) if code == "\x1b[0m"
                )
            except ValueError:
                pass

            # The active state is the sequence of codes after the last reset
            if last_reset_index != -1:
                active_codes = preceding_codes[last_reset_index + 1 :]
            else:
                active_codes = preceding_codes
            last_state = "".join(active_codes)

        return f"{colour_str(match.group()).back_green().black()}{last_state}"

    return find_and_replace


def send_serial_data(
    ser: serial.Serial, data: str, print_time: str, file: Any | None
) -> bool:
    """Send data to serial port and log it if logging is enabled."""
    try:
        # Add newline if not present (mimic readline behavior)
        if not data.endswith("\n"):
            data += "\n"

        # Send to serial port
        ser.write(data.encode("utf-8"))

        # Add timestamp and display/log sent data
        timestamped_line = f"{add_time_to_line(print_time)}{data}"
        print(timestamped_line, end="")

        if file:
            file.write(ASNI_ESCAPE_PATTERN.sub("", timestamped_line))

        return True
    except serial.SerialException as e:
        print(f"\n{colour_str('Send error:').red()} {e}")
        return False


def handle_user_input(
    ser: serial.Serial,
    print_time: str,
    file: Any | None,
    stop_event: threading.Event,
) -> None:
    """Handle user keyboard input for sending serial data."""
    while not stop_event.is_set():
        try:
            # Use select for non-blocking input detection (cross-platform)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.readline()
                if line:
                    # Remove trailing newline for processing
                    user_input = line.rstrip("\n")
                    if user_input:  # Don't send empty lines
                        send_serial_data(ser, user_input, print_time, file)
        except OSError:
            # Handle cases where stdin might not be available
            break
        except Exception as e:
            print(f"\n{colour_str('Input error:').red()} {e}")
            break


def serial_loop(
    ser: serial.Serial,
    print_time: str | None,
    file: Any | None,
    highlight_words: list[str] | None = None,
    enable_send: bool = False,
) -> None:
    # Create stop event for thread management
    stop_event = threading.Event()
    print_time = print_time or "none"
    input_thread = None

    # Start input thread if sending is enabled
    if enable_send:
        input_thread = threading.Thread(
            target=handle_user_input,
            args=(ser, print_time, file, stop_event),
            daemon=True,
        )
        input_thread.start()
        message = "Interactive sending enabled - type commands and press Enter:"
        print(f"{colour_str(message).green()}")

    try:
        while True:
            if not (line := ser.readline().decode("utf-8", errors="ignore")):
                continue
            line = f"{add_time_to_line(print_time)}{line}"
            if highlight_words:
                for word in highlight_words:
                    if not word:  # Skip empty strings from splitting
                        continue
                    line = re.sub(
                        re.escape(word),
                        create_replacement_lambda(line),
                        line,
                        flags=re.IGNORECASE,
                    )

            print(line, end="")
            if file:
                file.write(
                    ASNI_ESCAPE_PATTERN.sub("", line)
                )  # strip colours for log file
    finally:
        # Clean up input thread when exiting
        if input_thread and input_thread.is_alive():
            stop_event.set()
            input_thread.join(timeout=0.5)


def wait_with_spinner(serial_port_name: str, count: int) -> int:
    """Prints a spinning icon to show that the script is waiting."""
    loading_bars = ["[==    ]", "[  ==  ]", "[    ==]", "[  ==  ]"]
    loading_char = loading_bars[count % len(loading_bars)]

    # Construct the status text using your colour_str class
    status_text = str(
        colour_str(f"Waiting for {serial_port_name} {loading_char}").dim()
    )

    # Use carriage return '\r' to print over the same line
    sys.stdout.write(f"\r{status_text}")
    sys.stdout.flush()

    return count + 1


def run_serial_printing(
    serial_port_name: str,
    baud: int,
    print_time: str | None = None,
    file: Any | None = None,
    highlight_words: list[str] | None = None,
    enable_send: bool = False,
) -> None:
    count = 0
    while True:
        try:
            time.sleep(0.2)
            with serial.Serial(serial_port_name, baud, timeout=0.05) as ser:
                count = 0
                print("\n" + f" ✅ Connected to {serial_port_name} ".center(50, "-"))
                serial_loop(ser, print_time, file, highlight_words, enable_send)
        except serial.SerialException:
            count = wait_with_spinner(serial_port_name, count)
        except KeyboardInterrupt:
            print(colour_str(f"\nClosed {serial_port_name}.").dim().green())
            sys.exit(0)


def main() -> None:
    args = parse_arguments()

    if args.clear:
        clear_terminal()

    print(colour_str(f"{args}").dim())

    serial_port_name = get_serial_port_name(args.port)

    highlight_words = []
    if args.highlight:
        # Process a comma-separated string, also removing potential brackets
        highlight_words = args.highlight.strip("[]").split(",")

    if args.log:
        run_serial_printing_with_logs(
            serial_port_name,
            args.baud,
            args.log_file,
            args.log_directory,
            args.print_time,
            highlight_words,
            args.send,
        )
    else:
        run_serial_printing(
            serial_port_name,
            args.baud,
            args.print_time,
            None,
            highlight_words,
            args.send,
        )


if __name__ == "__main__":
    main()
