#!/usr/bin/env python3
import argparse
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

from . import __version__

try:
    MAX_WIDTH = min(shutil.get_terminal_size()[0], 80)
except (ValueError, OSError):
    MAX_WIDTH = 80


def has_crlf_endings(file_path: Path) -> bool:
    """Checks if a file has CRLF ('\\r\\n') line endings using pathlib features."""
    try:
        content = file_path.read_bytes()
        if b"\r\n" not in content:
            return False

        # Binary heuristic: Check for NULL byte
        if b"\0" in content:
            return False

        return True
    except (OSError, PermissionError) as e:
        print(f"Error reading file: {file_path} - {e}")
    return False


def scan_directory(root_path: Path, excluded_paths: set[Path]) -> Iterator[Path]:
    """
    Recursively yields files, skipping excluded directories.
    """
    try:
        # We iterate manually to allow pruning (skipping) directories efficiently
        for item in root_path.iterdir():
            if item.is_symlink():
                continue

            if item.is_dir():
                # Check exclusion before descending
                if item.resolve() in excluded_paths:
                    continue
                # Recurse
                yield from scan_directory(item, excluded_paths)
            else:
                yield item

    except PermissionError:
        print(f"⚠️  Permission denied: {root_path}")


def resolve_ignore_dirs(root: Path, ignore_patterns: list[str]) -> set[Path]:
    """
    Resolves ignore patterns (including globs) to absolute Path objects.
    """
    resolved_ignores = set()
    for pattern in ignore_patterns:
        for path in root.glob(pattern):
            if path.is_dir():
                resolved_ignores.add(path.resolve())

    return resolved_ignores


def check_crlf_in_root(
    repo_path: Path,
    ignore_patterns: list[str],
    verbose: bool = False,
    ignore_extensions: list[str] = [],
) -> None:
    if not repo_path.is_dir():
        print(f"Error: Directory not found at '{repo_path}'")
        sys.exit(1)

    print(f"🔍 Checking for CRLF line endings in: {repo_path}")

    # Resolve ignore patterns to actual paths
    ignored_dirs = resolve_ignore_dirs(repo_path, ignore_patterns)

    if verbose and ignored_dirs:
        print(" Ignored Directories ".center(MAX_WIDTH, "-"))
        for d in sorted(ignored_dirs):
            print(f"   🚫 {d}")

    ignored_exts = {ext.lstrip(".").lower() for ext in ignore_extensions}
    if verbose and ignored_exts:
        print(" Ignored Extensions ".center(MAX_WIDTH, "-"))
        for ext in sorted(ignored_exts):
            print(f"   🚫 *.{ext}")

    crlf_files_found = []

    # Use the custom scanner
    for file_path in scan_directory(repo_path, ignored_dirs):
        if file_path.suffix.lstrip(".").lower() in ignored_exts:
            continue
        if has_crlf_endings(file_path):
            # Calculate relative path for cleaner output using pathlib
            crlf_files_found.append(file_path.relative_to(repo_path))

    if crlf_files_found:
        print("🚨 Found files with CRLF line endings:")
        for file_path in sorted(crlf_files_found):
            print(f"  - {file_path}")
        sys.exit(1)
    else:
        print("✅ No files with CRLF line endings were found.")
        sys.exit(0)


def main() -> None:
    """Main entry point for CRLF checker."""
    parser = argparse.ArgumentParser(
        description="Checks for CRLF line endings in files within a repository.",
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # fmt: off
    parser.add_argument(
        "root_dir", nargs="?", default=".",
        help="The root directory to scan (default: current directory)"
    )
    parser.add_argument(
        "--ignore",
        "-i",
        nargs="+",
        metavar="DIR",
        default=[],
        help=(
            "One or more directories to ignore (accepts globs).\n"
            "(e.g., --ignore build dist '**/__pycache__')"
        ),
    )
    parser.add_argument(
        "--ignore-ext",
        "-e",
        nargs="+",
        metavar="EXT",
        default=[],
        help=(
            "One or more file extensions to ignore.\n"
            "(e.g., --ignore-ext log .log txt)"
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )
    args = parser.parse_args()
    # fmt: on

    try:
        check_crlf_in_root(
            repo_path=Path(args.root_dir).resolve(),
            ignore_patterns=args.ignore,
            verbose=args.verbose,
            ignore_extensions=args.ignore_ext,
        )
    except KeyboardInterrupt:
        print("Operation cancelled by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
