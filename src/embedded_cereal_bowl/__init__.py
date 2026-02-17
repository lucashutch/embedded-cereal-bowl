"""
Embedded Cereal Bowl - A collection of lightweight Python utilities for
embedded development.

This package provides tools for serial monitoring, code formatting, time conversion,
and line ending checking, designed to simplify common embedded development tasks.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("embedded-cereal-bowl")
except PackageNotFoundError:
    # Package is not installed
    __version__ = "0.0.0.dev0+unknown"

__author__ = "Lucas Hutch"

from . import formatter, monitor, timestamp, utils

__all__ = ["formatter", "monitor", "timestamp", "utils"]
