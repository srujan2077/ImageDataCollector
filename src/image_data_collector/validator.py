"""Validate image files and collect metadata from a stable byte snapshot."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image
from PIL import UnidentifiedImageError

from image_data_collector.scanner import SUPPORTED_EXTENSIONS

LOGGER = logging.getLogger(__name__)
SUPPORTED_FORMATS = frozenset({"JPEG", "PNG", "WEBP", "TIFF"})


@dataclass(frozen=True, slots=True)
class ValidationLimits:
    """Optional inclusive image dimension limits."""

    min_width: int | None = None
    max_width: int | None = None
    min_height: int | None = None
    max_height: int | None = None

    def __post_init__(self) -> None:
        limits = (self.min_width, self.max_width, self.min_height, self.max_height)
        if any(limit is not None and limit < 0 for limit in limits):
            raise ValueError("Image dimension limits cannot be negative")
        if self.min_width is not None and self.max_width is not None:
            if self.min_width > self.max_width:
                raise ValueError("min_width cannot exceed max_width")
        if self.min_height is not None and self.max_height is not None:
            if self.min_height > self.max_height:
                raise ValueError("min_height cannot exceed max_height")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Metadata and validation outcome for one image path."""

    path: Path
    relative_path: str
    filename: str
    image_format: str | None
    width: int | None
    height: int | None
    file_size_bytes: int | None
    sha256: str | None
    dimension_valid: bool
    is_valid: bool
    errors: tuple[str, ...]


def validate_image(
    path: Path,
    input_dir: Path | None = None,
    limits: ValidationLimits | None = None,
) -> ValidationResult:
    """Validate one supported image and return metadata without modifying it.

    The file is read once and Pillow decodes that same byte snapshot. A change
    detected while reading is reported as a validation error.
    """
    limits = limits or ValidationLimits()
    relative_path = _relative_path(path, input_dir)
    base = {
        "path": path,
        "relative_path": relative_path,
        "filename": path.name,
        "image_format": None,
        "width": None,
        "height": None,
        "file_size_bytes": None,
        "sha256": None,
        "dimension_valid": False,
        "is_valid": False,
        "errors": (),
    }

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return ValidationResult(**{**base, "errors": ("Unsupported file extension",)})

    try:
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
    except FileNotFoundError:
        return ValidationResult(**{**base, "errors": ("File not found",)})
    except OSError as error:
        LOGGER.warning("Could not read image %s: %s", path, error)
        return ValidationResult(**{**base, "errors": (f"Could not read file: {error}",)})

    errors: list[str] = []
    file_size = len(data)
    digest = hashlib.sha256(data).hexdigest()
    if before.st_size != file_size or after.st_size != file_size or before.st_mtime_ns != after.st_mtime_ns:
        errors.append("File changed during processing")

    image_format: str | None = None
    width: int | None = None
    height: int | None = None
    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            width, height = image.size
            if image_format not in SUPPORTED_FORMATS:
                errors.append(f"Unsupported image format: {image_format or 'unknown'}")
            frame_count = getattr(image, "n_frames", 1)
            for frame_number in range(frame_count):
                if frame_number:
                    image.seek(frame_number)
                image.load()
    except UnidentifiedImageError:
        errors.append("File is not a recognized image")
    except (OSError, SyntaxError, ValueError) as error:
        errors.append(f"Image could not be fully decoded: {error}")
    except Exception as error:  # Pillow may expose format-specific exceptions.
        LOGGER.warning("Unexpected error validating image %s: %s", path, error)
        errors.append(f"Image validation failed: {error}")

    dimension_valid = _dimensions_are_valid(width, height, limits)
    if width is not None and height is not None and not dimension_valid:
        errors.append("Image dimensions are outside configured limits")

    return ValidationResult(
        path=path,
        relative_path=relative_path,
        filename=path.name,
        image_format=image_format,
        width=width,
        height=height,
        file_size_bytes=file_size,
        sha256=digest,
        dimension_valid=dimension_valid,
        is_valid=not errors and dimension_valid,
        errors=tuple(errors),
    )


def _relative_path(path: Path, input_dir: Path | None) -> str:
    if input_dir is None:
        return path.name
    try:
        return path.relative_to(input_dir).as_posix()
    except ValueError:
        return path.name


def _dimensions_are_valid(
    width: int | None, height: int | None, limits: ValidationLimits
) -> bool:
    if width is None or height is None:
        return False
    return all(
        (
            limits.min_width is None or width >= limits.min_width,
            limits.max_width is None or width <= limits.max_width,
            limits.min_height is None or height >= limits.min_height,
            limits.max_height is None or height <= limits.max_height,
        )
    )
