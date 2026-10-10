
from pathlib import Path

import pymupdf

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".dart",
    ".js",
    ".ts",
    ".pdf",
}

MAX_EXTRACTED_CHARS = 100_000


def extract_text(file_path: Path) -> str | None:
    extension = file_path.suffix.lower()

    # Ignore unsupported file types.
    if extension not in SUPPORTED_EXTENSIONS:
        return None

    # Extract PDF text one page at a time.
    if extension == ".pdf":
        extracted_text = []

        with pymupdf.open(file_path) as document:
            for page in document:
                remaining = MAX_EXTRACTED_CHARS - sum(
                    len(text) for text in extracted_text
                )

                if remaining <= 0:
                    break

                page_text = page.get_text()
                extracted_text.append(page_text[:remaining])

        return "\n".join(extracted_text)

    # Read only up to the configured character limit.
    with file_path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as file:
        return file.read(MAX_EXTRACTED_CHARS)