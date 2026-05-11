#!/usr/bin/env python3
import argparse
import shutil
import subprocess  # nosec B404
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


def is_excluded(file_path: Path, excluded_paths: set[Path]) -> bool:
    """Return whether file_path is inside an excluded directory."""
    try:
        resolved = file_path.resolve()
    except OSError:
        return False
    return any(
        excluded == resolved or excluded in resolved.parents
        for excluded in excluded_paths
    )


def git_ls_files(root_dir: Path, verbose: bool) -> list[Path] | None:
    """Return git-tracked files rooted at root_dir, or None when git fails."""
    try:
        result = subprocess.run(  # nosec B603, B607
            ["git", "-C", str(root_dir), "ls-files", "-z", "--"],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        if verbose:
            print(f"⚠️  git ls-files failed; falling back to manual walk: {exc}")
        return None

    paths = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        file_path = root_dir / raw_path.decode("utf-8", "surrogateescape")
        if file_path.is_file() and not file_path.is_symlink():
            paths.append(file_path)
    return paths


def check_crlf_in_root(
    repo_path: Path,
    ignore_patterns: list[str],
    verbose: bool = False,
    ignore_extensions: list[str] | None = None,
    use_git_walk: bool = True,
) -> None:
    if not repo_path.is_dir():
        print(f"Error: Directory not found at '{repo_path}'")
        sys.exit(1)

    if isinstance(ignore_extensions, bool):
        use_git_walk = ignore_extensions
        ignore_extensions = None

    print(f"🔍 Checking for CRLF line endings in: {repo_path}")

    # Resolve ignore patterns to actual paths
    ignored_dirs = resolve_ignore_dirs(repo_path, ignore_patterns)

    if verbose and ignored_dirs:
        print(" Ignored Directories ".center(MAX_WIDTH, "-"))
        for d in sorted(ignored_dirs):
            print(f"   🚫 {d}")

    ignored_exts = {ext.lstrip(".").lower() for ext in (ignore_extensions or [])}
    if verbose and ignored_exts:
        print(" Ignored Extensions ".center(MAX_WIDTH, "-"))
        for ext in sorted(ignored_exts):
            print(f"   🚫 *.{ext}")

    crlf_files_found = []

    discovered_files = git_ls_files(repo_path, verbose) if use_git_walk else None
    if discovered_files is None:
        discovered_files = list(scan_directory(repo_path, ignored_dirs))

    for file_path in discovered_files:
        if is_excluded(file_path, ignored_dirs):
            continue
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
    parser.add_argument(
        "--no-git-walk",
        action="store_true",
        help="Use the legacy manual filesystem walk instead of git ls-files.",
    )
    args = parser.parse_args()
    # fmt: on

    try:
        check_crlf_in_root(
            repo_path=Path(args.root_dir).resolve(),
            ignore_patterns=args.ignore,
            verbose=args.verbose,
            ignore_extensions=args.ignore_ext,
            use_git_walk=not args.no_git_walk,
        )
    except KeyboardInterrupt:
        print("Operation cancelled by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
