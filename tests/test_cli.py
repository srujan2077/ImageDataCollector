import json
from pathlib import Path

import pytest
from PIL import Image

from image_data_collector.cli import main


def _create_image(path: Path, size: tuple[int, int] = (20, 10)) -> None:
    Image.new("RGB", size, color=(30, 60, 90)).save(path)


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as result:
        main(["--help"])

    assert result.value.code == 0
    assert "Validate images and create metadata reports" in capsys.readouterr().out


def test_cli_runs_pipeline_and_preserves_input_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "reports"
    input_dir.mkdir()
    image_path = input_dir / "sample.png"
    _create_image(image_path)
    original_bytes = image_path.read_bytes()

    exit_code = main(
        [
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--min-width",
            "10",
        ]
    )

    assert exit_code == 0
    assert image_path.read_bytes() == original_bytes
    assert (output_dir / "image_metadata.csv").is_file()
    assert json.loads((output_dir / "summary.json").read_text()) == {
        "total_processed": 1,
        "valid": 1,
        "invalid": 0,
        "duplicate": 0,
        "dimension_failures": 0,
    }
    assert "Total processed: 1" in capsys.readouterr().out


def test_cli_handles_missing_input_directory(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    exit_code = main(
        ["--input", str(tmp_path / "missing"), "--output", str(tmp_path / "reports")]
    )

    assert exit_code == 1
    assert "Input directory does not exist" in caplog.text
