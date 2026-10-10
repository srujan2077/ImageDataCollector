"""Command-line interface for the ImageDataCollector pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from image_data_collector.reporter import write_reports
from image_data_collector.scanner import scan_image_paths
from image_data_collector.validator import ValidationLimits, validate_image

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="image-data-collector",
        description="Validate images and create metadata reports.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Input image directory")
    parser.add_argument(
        "--output", required=True, type=Path, help="Output report directory"
    )
    parser.add_argument("--min-width", type=_non_negative_int, help="Minimum image width")
    parser.add_argument("--max-width", type=_non_negative_int, help="Maximum image width")
    parser.add_argument("--min-height", type=_non_negative_int, help="Minimum image height")
    parser.add_argument("--max-height", type=_non_negative_int, help="Maximum image height")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the image collection pipeline and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging()

    try:
        limits = ValidationLimits(
            min_width=args.min_width,
            max_width=args.max_width,
            min_height=args.min_height,
            max_height=args.max_height,
        )
    except ValueError as error:
        parser.error(str(error))

    if not args.input.exists():
        LOGGER.error("Input directory does not exist: %s", args.input)
        return 1
    if not args.input.is_dir():
        LOGGER.error("Input path is not a directory: %s", args.input)
        return 1

    try:
        image_paths = scan_image_paths(args.input)
        results = [validate_image(path, args.input, limits) for path in image_paths]
        _, summary_path = write_reports(results, args.output)
        summary = _read_summary(summary_path)
    except OSError as error:
        LOGGER.error("ImageDataCollector failed: %s", error)
        return 1

    _print_summary(summary)
    return 0


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _read_summary(summary_path: Path) -> dict[str, int]:
    with summary_path.open(encoding="utf-8") as summary_file:
        return json.load(summary_file)


def _print_summary(summary: dict[str, Any]) -> None:
    print(f"Total processed: {summary['total_processed']}")
    print(f"Valid: {summary['valid']}")
    print(f"Invalid: {summary['invalid']}")
    print(f"Duplicate: {summary['duplicate']}")
    print(f"Dimension failures: {summary['dimension_failures']}")


if __name__ == "__main__":
    sys.exit(main())
