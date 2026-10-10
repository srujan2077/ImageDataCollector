"""Discover supported image files without modifying the input directory."""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)
SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"})


def scan_image_paths(input_dir: Path) -> list[Path]:
    """Return supported image files below ``input_dir`` in deterministic order.

    Missing directories and directories that cannot be traversed are reported via
    logging and result in an empty list. Files with unsupported extensions are
    ignored; no filesystem contents are changed.
    """
    if not input_dir.exists():
        LOGGER.warning("Input directory does not exist: %s", input_dir)
        return []

    if not input_dir.is_dir():
        LOGGER.warning("Input path is not a directory: %s", input_dir)
        return []

    try:
        paths = [
            path
            for path in input_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
    except OSError as error:
        LOGGER.error("Could not scan input directory %s: %s", input_dir, error)
        return []

    return sorted(paths, key=lambda path: path.relative_to(input_dir).as_posix().lower())
