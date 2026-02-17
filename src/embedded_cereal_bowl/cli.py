"""Console script entry points for embedded-cereal-bowl package."""

import sys

from . import check_crlf
from .formatter import main as formatter_main
from .monitor import main as monitor_main
from .timestamp import main as timestamp_main


def main_monitor() -> None:
    """Entry point for the monitor console script."""
    return monitor_main()


def main_timestamp() -> None:
    """Entry point for the timestamp console script."""
    return timestamp_main()


def main_check_crlf() -> None:
    """Entry point for the check-crlf console script."""
    return check_crlf.main()


def main_formatter() -> None:
    """Entry point for the format-code console script."""
    return formatter_main()


def main_cli() -> None:
    """Main entry point for the CLI tool dispatcher."""
    # Allow running this module directly for testing
    if len(sys.argv) > 1:
        tool = sys.argv[1]
        if tool == "monitor":
            sys.argv.pop(1)
            main_monitor()
        elif tool == "timestamp":
            sys.argv.pop(1)
            main_timestamp()
        elif tool == "check-crlf":
            sys.argv.pop(1)
            main_check_crlf()
        elif tool == "format-code":
            sys.argv.pop(1)
            main_formatter()
        else:
            print(
                "Usage: python -m embedded_cereal_bowl.cli "
                "[monitor|timestamp|check-crlf|format-code] [args]"
            )
            sys.exit(1)
    else:
        print(
            "Usage: python -m embedded_cereal_bowl.cli "
            "[monitor|timestamp|check-crlf|format-code] [args]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
