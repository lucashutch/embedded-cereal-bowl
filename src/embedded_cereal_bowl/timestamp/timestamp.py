#!/usr/bin/env python3
import argparse
import sys
from datetime import UTC, datetime

from .. import __version__


def parse_and_convert_time(time_input: str) -> tuple[str, str, float]:
    """
    Parses the time input (timestamp or ISO 8601 string) and
    converts it to UTC ISO string, local ISO string, and UTC timestamp.
    """
    # Get local timezone info
    local_tz = datetime.now().astimezone().tzinfo

    try:
        # 1. Attempt to parse as a float (timestamp)
        ts = float(time_input)

        # Detect milliseconds (if timestamp is very large, assume ms)
        if ts > 1e12:
            ts /= 1000.0

        # Convert timestamp to an aware datetime object in UTC
        dt_aware = datetime.fromtimestamp(ts, tz=UTC)

    except ValueError:
        # 2. If float conversion fails, attempt to parse as an ISO 8601 string
        time_string = time_input.strip()

        try:
            # datetime.fromisoformat() handles 'Z' and offsets like '+10:30' directly
            dt_aware = datetime.fromisoformat(time_string)

            # If the resulting datetime object is naive, assume UTC
            if dt_aware.tzinfo is None or dt_aware.tzinfo.utcoffset(dt_aware) is None:
                dt_aware = dt_aware.replace(tzinfo=UTC)

        except ValueError as e:
            # Re-raise the error with a helpful message
            raise ValueError(
                f"Input '{time_input}' is neither a valid Unix timestamp nor "
                f"a valid ISO 8601 string."
            ) from e

    # Convert the aware datetime object to the target timezones
    dt_utc = dt_aware.astimezone(UTC)
    dt_local = dt_aware.astimezone(local_tz)

    # Format as ISO 8601 with milliseconds
    # Replace '+00:00' with 'Z' for UTC output
    utc_str = dt_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    local_str = dt_local.isoformat(timespec="milliseconds")

    # Get timestamp in seconds
    utc_ts = dt_utc.timestamp()

    return utc_str, local_str, utc_ts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a Unix timestamp (seconds/milliseconds) or an ISO 8601 "
        "time string to UTC and local time in ISO 8601 format."
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    # The argument type is str to handle both numeric and string date formats
    parser.add_argument(
        "time_input",
        type=str,
        help="Time value (e.g., 1761660634.104 or 2025-10-26T14:10:34.104Z)",
    )

    args = parser.parse_args()

    try:
        utc_str, local_str, utc_ts = parse_and_convert_time(args.time_input)

        # Re-ordered slightly to put the timestamp first or last,
        # aligned based on the length of "Timestamp:"
        print(f"Timestamp: {int(utc_ts)}")
        print(f"UTC:       {utc_str}")
        print(f"Local:     {local_str}")

    except ValueError as e:
        print(f"Error: {e}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
