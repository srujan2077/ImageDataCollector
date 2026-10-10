import hashlib
from pathlib import Path

from PIL import Image

from image_data_collector.validator import ValidationLimits, validate_image


def _create_image(path: Path, size: tuple[int, int] = (20, 10)) -> None:
    image = Image.new("RGB", size, color=(40, 80, 120))
    image.save(path)


def test_validate_records_metadata_for_valid_image(tmp_path: Path) -> None:
    image_path = tmp_path / "photo.png"
    _create_image(image_path)

    result = validate_image(image_path, tmp_path)

    assert result.is_valid
    assert result.relative_path == "photo.png"
    assert result.image_format == "PNG"
    assert (result.width, result.height) == (20, 10)
    assert result.file_size_bytes == image_path.stat().st_size
    assert result.sha256 == hashlib.sha256(image_path.read_bytes()).hexdigest()
    assert result.errors == ()


def test_validate_rejects_corrupt_image(tmp_path: Path) -> None:
    image_path = tmp_path / "corrupt.jpg"
    image_path.write_bytes(b"not an image")

    result = validate_image(image_path, tmp_path)

    assert not result.is_valid
    assert result.sha256 is not None
    assert any("recognized image" in error for error in result.errors)


def test_validate_enforces_dimension_limits(tmp_path: Path) -> None:
    image_path = tmp_path / "small.png"
    _create_image(image_path, (20, 10))

    result = validate_image(
        image_path,
        tmp_path,
        ValidationLimits(min_width=21, max_height=10),
    )

    assert not result.is_valid
    assert not result.dimension_valid
    assert "Image dimensions are outside configured limits" in result.errors


def test_identical_images_have_identical_hashes(tmp_path: Path) -> None:
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    _create_image(first_path)
    second_path.write_bytes(first_path.read_bytes())

    first = validate_image(first_path, tmp_path)
    second = validate_image(second_path, tmp_path)

    assert first.is_valid and second.is_valid
    assert first.sha256 == second.sha256


def test_validate_missing_file_returns_structured_failure(tmp_path: Path) -> None:
    result = validate_image(tmp_path / "missing.png", tmp_path)

    assert not result.is_valid
    assert result.file_size_bytes is None
    assert result.sha256 is None
    assert result.errors == ("File not found",)
