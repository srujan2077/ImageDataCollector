from pathlib import Path

from image_data_collector.scanner import scan_image_paths


def test_scan_finds_supported_images_recursively(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    nested_dir = input_dir / "nested"
    nested_dir.mkdir(parents=True)
    expected = [input_dir / "photo.JPG", nested_dir / "scan.tiff"]
    for path in expected:
        path.write_bytes(b"placeholder")
    (input_dir / "notes.txt").write_text("ignore me", encoding="utf-8")

    result = scan_image_paths(input_dir)

    assert result == sorted(expected, key=lambda path: path.relative_to(input_dir).as_posix().lower())


def test_scan_missing_directory_returns_empty_list_and_logs_warning(
    tmp_path: Path, caplog: object
) -> None:
    missing_dir = tmp_path / "missing"

    result = scan_image_paths(missing_dir)

    assert result == []
    assert "does not exist" in caplog.text
