import os
from pathlib import Path


def scan_files(root_path: str):
    root = Path(root_path).expanduser().resolve()

    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")

    scanned = 0
    errors = 0

    def handle_error(error):
        nonlocal errors
        errors += 1
        print(f"Skipped inaccessible location: {error}")

    for current_dir, _, filenames in os.walk(
        root,
        onerror=handle_error,
        followlinks=False,
    ):
        for filename in filenames:
            file_path = Path(current_dir) / filename

            try:
                if file_path.is_symlink():
                    continue

                stat = file_path.stat()

                yield {
                    "name": file_path.name,
                    "path": str(file_path),
                    "extension": file_path.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "modified_at": stat.st_mtime,
                }

                scanned += 1

            except OSError as error:
                errors += 1
                print(f"Skipped file: {file_path} ({error})")

    print(f"Files scanned: {scanned}")
    print(f"Errors encountered: {errors}")