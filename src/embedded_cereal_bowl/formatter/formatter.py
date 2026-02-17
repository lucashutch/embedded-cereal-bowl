#!/usr/bin/env python3

import argparse
import concurrent.futures
import difflib
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

from .. import __version__
from ..utils.color_utils import colour_str

try:
    MAX_WIDTH = min(shutil.get_terminal_size()[0], 80)
except (ValueError, OSError):
    MAX_WIDTH = 80

FORMATTER_CONFIG: dict[str, dict[str, Any]] = {
    "clang-format": {
        "command": "clang-format",
        "file_extensions": {".h", ".hpp", ".hxx", ".hh", ".c", ".cpp", ".cxx", ".cc"},
        "file_names": set(),
    },
    "cmake-format": {
        "command": "cmake-format",
        "file_extensions": {".cmake"},
        "file_names": {"CMakeLists.txt"},
    },
}


def resolve_ignore_dirs(root: Path, patterns: list[str]) -> set[Path]:
    """
    Resolves a list of ignore patterns (e.g., 'build', '**/vendor', '*/temp')
    into a set of absolute Path objects.
    """
    resolved = set()
    for pattern in patterns:
        # pathlib glob allows patterns like '**/build' or 'build'
        for path in root.glob(pattern):
            if path.is_dir():
                resolved.add(path.resolve())
    return resolved


def scan_directory(
    root_path: Path, excluded_paths: set[Path]
) -> Generator[Path, None, None]:
    """
    Recursively yields files, skipping excluded directories.
    Uses pathlib.iterdir() for manual traversal control.
    """
    try:
        for item in root_path.iterdir():
            if item.is_symlink():
                continue

            if item.is_dir():
                # If this directory is in our exclusion list, skip it entirely
                if item.resolve() in excluded_paths:
                    continue
                yield from scan_directory(item, excluded_paths)
            else:
                yield item
    except PermissionError:
        print(f"⚠️  Permission denied: {root_path}", file=sys.stderr)


def find_all_files(
    root_dir: Path, ignore_patterns: list[str], verbose: bool
) -> dict[Path, dict[str, Any]]:
    """Finds all files for all configured formatters, respecting ignore globs."""

    files_with_config: dict[Path, dict[str, Any]] = {}

    if not root_dir.is_dir():
        msg = f"Error: Root directory '{root_dir}' not found."
        print(colour_str(msg).red(), file=sys.stderr)
        sys.exit(1)

    absolute_ignore_dirs = resolve_ignore_dirs(root_dir, ignore_patterns)

    if verbose and ignore_patterns:
        print(" Ignored Directories ".center(MAX_WIDTH, "-"))
        if not absolute_ignore_dirs:
            print("  (No directories matched the ignore patterns)")
        for d in sorted(absolute_ignore_dirs):
            print(f"  🚫 {d}")

    name_lookup = {
        name: config
        for config in FORMATTER_CONFIG.values()
        for name in config.get("file_names", [])
    }
    extension_lookup = {
        ext: config
        for config in FORMATTER_CONFIG.values()
        for ext in config.get("file_extensions", [])
    }

    for file_path in scan_directory(root_dir, absolute_ignore_dirs):
        config = name_lookup.get(file_path.name)
        if not config:
            config = extension_lookup.get(file_path.suffix)
        if config:
            files_with_config[file_path] = config

    return files_with_config


def process_one_file(
    file_path: Path, command: str, check: bool
) -> tuple[str, bool, str | None]:
    """
    Worker function to either check or format a single file.
    In check mode, it returns a diff; otherwise, it formats in-place.
    """
    try:
        original_content = file_path.read_bytes()
        cmd_args = [command, str(file_path)]
        if not check:
            cmd_args.append("-i")  # In-place flag

        result = subprocess.run(cmd_args, check=True, capture_output=True)  # nosec B603

        if check:
            # In check mode, stdout usually contains the formatted file content
            new_content = result.stdout
        else:
            # In in-place mode, we must re-read the file to compare
            new_content = file_path.read_bytes()

        if original_content == new_content:
            return (str(file_path), False, None)

        if not check:
            return (str(file_path), True, None)

        # Generate a diff for check mode
        original_lines = original_content.decode("utf-8", "ignore").splitlines()
        new_lines = new_content.decode("utf-8", "ignore").splitlines()

        diff = difflib.unified_diff(original_lines, new_lines, lineterm="")

        # Filter for just the changes (skipping the +++ and --- headers)
        changed_lines = [
            line
            for line in diff
            if (line.startswith("+") and not line.startswith("+++"))
            or (line.startswith("-") and not line.startswith("---"))
        ]
        return (str(file_path), True, "\n".join(changed_lines))

    except Exception as e:
        error_type = "checking" if check else "formatting"
        print(colour_str(f"Error {error_type} {file_path}: {e}").red(), file=sys.stderr)
        return (str(file_path), False, None)


def process_files_parallel(
    files_with_config: dict[Path, dict[str, Any]],
    project_root: Path,
    jobs: int | None,
    verbose: bool,
    check: bool,
) -> None:
    """Runs the correct formatter or checker in parallel for all found files."""
    if not files_with_config:
        print("No files found to process.")
        return

    if verbose:
        print(" Files Found ".center(MAX_WIDTH, "-"))
        for f in sorted(files_with_config.keys()):
            print(f"  📄 {f.relative_to(project_root)}")

    job_type = "Checking" if check else "Formatting"
    job_str = f"{job_type} using {jobs if jobs else 'all available'} cores"
    print(f"🚀 Found {len(files_with_config)} files. {job_str}.")

    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as executor:
        future_to_file = {
            executor.submit(process_one_file, path, config["command"], check): path
            for path, config in files_with_config.items()
        }
        for future in concurrent.futures.as_completed(future_to_file):
            try:
                path_str, was_changed, data = future.result()
                if was_changed:
                    # Convert string back to Path for relative_to calc
                    rel_path = Path(path_str).relative_to(project_root)
                    results.append((str(rel_path), data))
            except Exception as e:
                msg = f"A task generated an exception: {e}"
                print(colour_str(msg).red(), file=sys.stderr)

    if check:
        if not results:
            msg = "✅ Check passed. All files are correctly formatted."
            print(colour_str(msg).green())
            return

        print("\n" + " Files Requiring Formatting ".center(MAX_WIDTH, "-"))
        for f_path, diff_text in sorted(results):
            print(f"\n{colour_str(f'❌ {f_path}').yellow()}")
            if diff_text:
                for line in diff_text.splitlines():
                    if line.startswith("+"):
                        print(colour_str(line).green())
                    elif line.startswith("-"):
                        print(colour_str(line).red())
        msg = f"❌ Check failed. {len(results)} files require formatting."
        print(f"\n{colour_str(msg).red().bright()}")
        sys.exit(1)

    else:
        if not results:
            print("✅ All files are already correctly formatted. No changes made.")
            return

        print(" Files Reformatted ".center(MAX_WIDTH, "-"))
        for f_path, _ in sorted(results):
            print(colour_str(f"  ✨ {f_path}").green())
        print(f"✅ Done. {len(results)} files were reformatted.")


def run_project_tasks(
    root_dir: Path,
    ignore_patterns: list[str] = [],
    jobs: int | None = None,
    check: bool = False,
    verbose: bool = False,
) -> None:
    print(f"🚀 Scanning for all source files in: {root_dir}")
    files_to_process = find_all_files(root_dir, ignore_patterns, verbose)
    process_files_parallel(files_to_process, root_dir, jobs, verbose, check)


def check_for_tools() -> bool:
    all_tools_found = True
    # Check if tools exist using shutil.which (cleaner than subprocess)
    for config in FORMATTER_CONFIG.values():
        command = config["command"]
        if shutil.which(command) is None:
            print(colour_str(f"❌ Error: '{command}' not found in PATH.").red())
            all_tools_found = False

    return all_tools_found


def main() -> None:
    """Main entry point for the formatter."""
    parser = argparse.ArgumentParser(
        description=(
            "A universal script to format all source files (C++, CMake, "
            "etc.) in parallel."
        )
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
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
        metavar="PATTERN",
        default=[],
        help=(
            "One or more directory patterns to ignore.\n"
            "(e.g., --ignore build '**/__pycache__' '*/temp')"
        ),
    )

    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=None,
        help=(
            "The number of concurrent jobs to run.\n"
            "(default: all available CPU cores)"
        ),
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose output."
    )

    parser.add_argument(
        "--check",
        "-c",
        action="store_true",
        help=(
            "Run in 'check only' mode. Outputs files requiring "
            "changes and the associated required changes"
        ),
    )
    args = parser.parse_args()
    # fmt: on

    if not check_for_tools():
        sys.exit(1)
    try:
        run_project_tasks(
            root_dir=Path(args.root_dir).resolve(),
            ignore_patterns=args.ignore,
            jobs=args.jobs,
            check=args.check,
            verbose=args.verbose,
        )
    except KeyboardInterrupt:
        print("Operation cancelled by user.")
        sys.exit(130)


def format_files(
    root_dir: str = ".",
    ignore_patterns: list[str] | None = None,
    jobs: int | None = None,
    verbose: bool = False,
) -> None:
    """Format files in a directory (for programmatic use)."""
    if not check_for_tools():
        return
    run_project_tasks(
        root_dir=Path(root_dir).resolve(),
        ignore_patterns=ignore_patterns or [],
        jobs=jobs,
        check=False,
        verbose=verbose,
    )


def check_format(
    root_dir: str = ".",
    ignore_patterns: list[str] | None = None,
    jobs: int | None = None,
    verbose: bool = False,
) -> None:
    """Check file formatting in a directory (for programmatic use)."""
    if not check_for_tools():
        return
    run_project_tasks(
        root_dir=Path(root_dir).resolve(),
        ignore_patterns=ignore_patterns or [],
        jobs=jobs,
        check=True,
        verbose=verbose,
    )


if __name__ == "__main__":
    main()
