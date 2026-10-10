"""Write deterministic CSV and JSON reports from image validation results."""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from image_data_collector.validator import ValidationResult

LOGGER = logging.getLogger(__name__)
CSV_COLUMNS = (
    "relative_path",
    "filename",
    "format",
    "width",
    "height",
    "file_size_bytes",
    "sha256",
    "validation_status",
    "validation_errors",
    "duplicate_status",
)
SUMMARY_KEYS = (
    "total_processed",
    "valid",
    "invalid",
    "duplicate",
    "dimension_failures",
)


def write_reports(
    results: Iterable[ValidationResult], output_dir: Path
) -> tuple[Path, Path]:
    """Write ``image_metadata.csv`` and ``summary.json`` to ``output_dir``.

    Results are sorted by relative path for deterministic output. Duplicate
    status is derived from repeated non-null SHA-256 hashes. The source image
    paths are only read from the supplied result objects and never modified.

    Returns:
        Paths to the CSV and JSON files, in that order.

    Raises:
        OSError: If the output directory or report files cannot be written.
    """
    ordered_results = sorted(
        results,
        key=lambda result: (result.relative_path.lower(), result.relative_path),
    )
    duplicate_hashes = {
        image_hash
        for image_hash, count in Counter(
            result.sha256 for result in ordered_results if result.sha256 is not None
        ).items()
        if count > 1
    }

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / "image_metadata.csv"
        summary_path = output_dir / "summary.json"
        _write_csv(csv_path, ordered_results, duplicate_hashes)
        _write_summary(summary_path, ordered_results)
    except OSError as error:
        LOGGER.error("Could not write reports to %s: %s", output_dir, error)
        raise

    return csv_path, summary_path


def _write_csv(
    csv_path: Path,
    results: list[ValidationResult],
    duplicate_hashes: set[str],
) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "relative_path": result.relative_path,
                    "filename": result.filename,
                    "format": result.image_format or "",
                    "width": _as_csv_value(result.width),
                    "height": _as_csv_value(result.height),
                    "file_size_bytes": _as_csv_value(result.file_size_bytes),
                    "sha256": result.sha256 or "",
                    "validation_status": "valid" if result.is_valid else "invalid",
                    "validation_errors": "; ".join(result.errors),
                    "duplicate_status": _duplicate_status(result, duplicate_hashes),
                }
            )


def _write_summary(summary_path: Path, results: list[ValidationResult]) -> None:
    summary = {
        "total_processed": len(results),
        "valid": sum(result.is_valid for result in results),
        "invalid": sum(not result.is_valid for result in results),
        "duplicate": sum(
            result.sha256 is not None
            for result in results
            if _is_duplicate_hash(result, results)
        ),
        "dimension_failures": sum(
            "Image dimensions are outside configured limits" in result.errors
            for result in results
        ),
    }
    with summary_path.open("w", encoding="utf-8", newline="\n") as summary_file:
        json.dump(summary, summary_file, indent=2)
        summary_file.write("\n")


def _duplicate_status(result: ValidationResult, duplicate_hashes: set[str]) -> str:
    if result.sha256 is None:
        return "unavailable"
    return "duplicate" if result.sha256 in duplicate_hashes else "unique"


def _is_duplicate_hash(result: ValidationResult, results: list[ValidationResult]) -> bool:
    return result.sha256 is not None and sum(
        other.sha256 == result.sha256 for other in results
    ) > 1


def _as_csv_value(value: int | None) -> int | str:
    return "" if value is None else value
