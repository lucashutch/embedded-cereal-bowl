#!/usr/bin/env python3

import argparse
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from . import __version__


def cleanup_logs(log_path: Path) -> None:
    """
    Zips the specified log directory with a timestamp and then deletes the
    original directory.
    """

    # Determine the directory where the archive will be saved (its parent)
    archive_base_dir = log_path.parent
    log_folder_name = log_path.name

    print(f"Starting cleanup for folder: {log_path.resolve()}")

    if not log_path.is_dir():
        print(f"Error: The directory '{log_path}' was not found.")
        print("Please check the directory name or path.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Archive name is constructed relative to its save location
    archive_filename = archive_base_dir / f"{log_folder_name}-{timestamp}.zip"

    print(f"Creating archive: {archive_filename.name} in {archive_base_dir.resolve()}")
    try:
        with zipfile.ZipFile(archive_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in log_path.glob("**/*"):
                if file_path.is_file():
                    # Relative to the parent, to put the log_folder_name inside the zip
                    arcname = file_path.relative_to(archive_base_dir)
                    zipf.write(file_path, arcname)

        print("Archive created successfully.")
        print(f"Deleting original folder: {log_path.name}")
        shutil.rmtree(log_path)
        print(f"Cleanup complete! '{log_path.name}' has been zipped and deleted.")

    except Exception as e:
        print(f"An error occurred during the process: {e}")
        print("The original logs folder was NOT deleted due to the error.")


# --- Argument Parsing and Execution ---
def main() -> None:
    """Main entry point for archive logs utility."""
    parser = argparse.ArgumentParser(
        description=(
            "Archive a specified log directory with a timestamp and then delete it."
        )
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default=Path("logs"),
        type=Path,
        help="The path or name of the directory to archive. Default: 'logs'",
    )

    args = parser.parse_args()

    # If the user provided a relative path/name, we resolve it relative to the CWD
    log_path_to_archive = Path.cwd() / args.directory
    cleanup_logs(log_path_to_archive)


if __name__ == "__main__":
    main()
