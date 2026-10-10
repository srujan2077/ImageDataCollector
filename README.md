# ImageDataCollector

ImageDataCollector is a read-only Python command-line tool for inspecting local
image files. It recursively finds supported images, validates that each file can
be fully decoded, records image and file metadata, applies optional dimension
limits, identifies byte-identical files with SHA-256 hashes, and writes
deterministic CSV and JSON reports. Source images are never modified.

## Key features

- Recursive scanning of an input directory in deterministic path order.
- Validation of image contents, including multi-frame images.
- Width and height limits supplied at runtime.
- File size and SHA-256 metadata.
- Duplicate detection based on repeated SHA-256 values.
- A row for every discovered supported file, including invalid files.
- Machine-readable CSV and JSON reports plus a terminal summary.

## Supported image formats

The scanner accepts files with these extensions (case-insensitive):

- JPEG: `.jpg`, `.jpeg`
- PNG: `.png`
- WebP: `.webp`
- TIFF: `.tif`, `.tiff`

The extension is only the first filter; Pillow also validates the image
contents and decoded format.

## Installation on Windows

From the project directory, create and activate a Python 3.12-or-newer virtual
environment in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

The editable install provides the `image-data-collector` console command and
installs the test dependencies. If PowerShell blocks script activation, use
`Set-ExecutionPolicy -Scope Process Bypass` for the current PowerShell
session, then run the activation command again.

## CLI usage

The installed entry point is `image-data-collector`, defined by the project as
`image_data_collector.cli:main`:

```powershell
image-data-collector --input data\input --output data\output
```

Both `--input` and `--output` are required. The output directory is created
when needed. Optional inclusive dimension limits are specified in pixels:

```powershell
image-data-collector `
  --input data\input `
  --output data\output `
  --min-width 800 `
  --max-width 6000 `
  --min-height 600 `
  --max-height 4000
```

Arguments:

- `--input`: existing directory to scan recursively.
- `--output`: directory for the generated reports.
- `--min-width`, `--max-width`: optional non-negative width limits.
- `--min-height`, `--max-height`: optional non-negative height limits.

The command returns a non-zero exit code for a missing or non-directory input
path, or a fatal report-writing error. Individual invalid images are reported
and do not stop the rest of the scan.

## Output schemas

### `image_metadata.csv`

The CSV has one row per supported file, sorted by relative path, with these
columns:

| Column | Contents |
| --- | --- |
| `relative_path` | Path below the input directory, using `/` separators |
| `filename` | File name |
| `format` | Decoded Pillow format, such as `PNG` or `JPEG`; blank if unavailable |
| `width` | Width in pixels; blank if unavailable |
| `height` | Height in pixels; blank if unavailable |
| `file_size_bytes` | Bytes read from the file; blank if unreadable |
| `sha256` | SHA-256 of the bytes read; blank if unreadable |
| `validation_status` | `valid` or `invalid` |
| `validation_errors` | Semicolon-separated validation errors; blank when valid |
| `duplicate_status` | `unique`, `duplicate`, or `unavailable` |

### `summary.json`

The JSON object always contains integer counts for:

```json
{
  "total_processed": 0,
  "valid": 0,
  "invalid": 0,
  "duplicate": 0,
  "dimension_failures": 0
}
```

`duplicate` counts rows whose non-null SHA-256 occurs more than once.
`dimension_failures` counts rows with an image dimension outside the configured
limits.

## Tests

Run pytest from the project directory after activating the virtual environment:

```powershell
python -m pytest
```

## Two-image smoke test

The repository includes `data\smoke-input\sample1.png` and
`data\smoke-input\sample2.jpg`. With the virtual environment active, run:

```powershell
image-data-collector `
  --input data\smoke-input `
  --output data\smoke-output-temp
```

The command prints:

```text
Total processed: 2
Valid: 2
Invalid: 0
Duplicate: 0
Dimension failures: 0
```

It writes `image_metadata.csv` with two valid rows (PNG 640x480 and JPEG
800x600) and `summary.json` with the same counts. The temporary output
directory is ignored by Git.

## Current limitations

- The tool only inspects image files already present on the local filesystem.
- Website scraping is not implemented.
- Image downloading is not implemented.
- Client-specific metadata requirements are not inferred.
- Source images are not modified or transformed.
