import csv
import json
from pathlib import Path

from image_data_collector.reporter import CSV_COLUMNS, write_reports
from image_data_collector.validator import ValidationResult


def _result(
    relative_path: str,
    *,
    is_valid: bool = True,
    dimension_valid: bool = True,
    sha256: str | None = "a" * 64,
    errors: tuple[str, ...] = (),
) -> ValidationResult:
    path = Path(relative_path)
    return ValidationResult(
        path=path,
        relative_path=relative_path,
        filename=path.name,
        image_format="PNG",
        width=20,
        height=10,
        file_size_bytes=100,
        sha256=sha256,
        dimension_valid=dimension_valid,
        is_valid=is_valid,
        errors=errors,
    )


def test_write_reports_creates_expected_csv_rows_and_headers(tmp_path: Path) -> None:
    results = [
        _result("z-last.png", sha256="b" * 64),
        _result("a-first.png"),
        _result("nested/a-copy.png"),
    ]

    csv_path, _ = write_reports(results, tmp_path / "reports")

    with csv_path.open(encoding="utf-8", newline="") as report_file:
        rows = list(csv.DictReader(report_file))
    assert list(rows[0]) == list(CSV_COLUMNS)
    assert [row["relative_path"] for row in rows] == [
        "a-first.png",
        "nested/a-copy.png",
        "z-last.png",
    ]
    assert rows[0]["validation_status"] == "valid"
    assert rows[0]["duplicate_status"] == "duplicate"
    assert rows[1]["duplicate_status"] == "duplicate"
    assert rows[2]["duplicate_status"] == "unique"


def test_write_reports_creates_summary_counts(tmp_path: Path) -> None:
    results = [
        _result("valid.png"),
        _result("duplicate.png"),
        _result(
            "bad-dimensions.png",
            is_valid=False,
            dimension_valid=False,
            sha256="c" * 64,
            errors=("Image dimensions are outside configured limits",),
        ),
        _result(
            "corrupt.png",
            is_valid=False,
            dimension_valid=False,
            sha256=None,
            errors=("File is not a recognized image",),
        ),
    ]
    results[1] = _result("duplicate.png")

    _, summary_path = write_reports(results, tmp_path / "reports")

    assert json.loads(summary_path.read_text(encoding="utf-8")) == {
        "total_processed": 4,
        "valid": 2,
        "invalid": 2,
        "duplicate": 2,
        "dimension_failures": 1,
    }


def test_write_reports_handles_empty_results_and_creates_output_directory(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "nested" / "reports"

    csv_path, summary_path = write_reports([], output_dir)

    assert output_dir.is_dir()
    assert csv_path.read_text(encoding="utf-8") == ",".join(CSV_COLUMNS) + "\n"
    assert json.loads(summary_path.read_text(encoding="utf-8")) == {
        "total_processed": 0,
        "valid": 0,
        "invalid": 0,
        "duplicate": 0,
        "dimension_failures": 0,
    }
