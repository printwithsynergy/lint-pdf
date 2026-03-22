---
title: "Hot Folder Integration"
description: "Automatically preflight files by dropping them into a watched directory. The LintPDF hot folder monitors a local directory and submits new files to the API."
section: "integrations"
order: 11
---

# Hot Folder Integration

The LintPDF hot folder is a standalone CLI tool that monitors a local directory for new files and automatically submits them to the LintPDF API. Files are routed to pass, fail, or error directories based on preflight results.

This runs on **your machine** — it's a client-side tool, not a server feature.

## Installation

```bash
pip install lintpdf-hotfolder
```

Or install from source:

```bash
cd packages/hotfolder
pip install -e .
```

## Quick Start

```bash
# Watch a directory and route files based on results
lintpdf-watch \
  --watch-dir /path/to/incoming \
  --api-key lpdf_your_api_key \
  --profile gwg-sheetfed \
  --pass-dir /path/to/approved \
  --fail-dir /path/to/rejected \
  --error-dir /path/to/errors
```

Drop a PDF into `/path/to/incoming` and the tool will:

1. Detect the new file
2. Wait for the file to be fully written (stabilization check)
3. Submit it to LintPDF
4. Poll for results
5. Move it to `approved/` or `rejected/` based on pass/fail
6. Write a JSON sidecar report alongside the moved file

## Directory Layout

```
/incoming/          ← Drop files here (watched directory)
    artwork.pdf     ← New file detected

/approved/          ← Files that passed preflight
    artwork.pdf
    artwork.pdf.lintpdf.json    ← Sidecar report

/rejected/          ← Files that failed preflight
    label.pdf
    label.pdf.lintpdf.json

/errors/            ← Files that couldn't be processed
    corrupt.pdf
    corrupt.pdf.lintpdf.json    ← Contains error details
```

## Command-Line Options

```
Usage: lintpdf-watch [OPTIONS]

Options:
  --watch-dir PATH          Directory to watch for new files (required)
  --api-key TEXT            LintPDF API key (or set LINTPDF_API_KEY env var)
  --base-url TEXT           API base URL [default: https://api.lintpdf.com]
  --profile TEXT            Voyage Plan profile ID [default: grounded-default]
  --pass-dir PATH           Move passed files here
  --fail-dir PATH           Move failed files here
  --error-dir PATH          Move errored files here
  --sidecar / --no-sidecar  Write JSON sidecar reports [default: --sidecar]
  --stabilization FLOAT     Seconds to wait for file stability [default: 2.0]
  --poll-interval FLOAT     Seconds between status polls [default: 5.0]
  --log-level TEXT          Log level (DEBUG, INFO, WARNING, ERROR) [default: INFO]
  --help                    Show this message and exit.
```

## Configuration via Environment Variables

```bash
export LINTPDF_API_KEY=lpdf_your_api_key
export LINTPDF_BASE_URL=https://api.lintpdf.com
export LINTPDF_PROFILE=gwg-sheetfed

lintpdf-watch --watch-dir /incoming --pass-dir /approved --fail-dir /rejected
```

## Sidecar Report Format

When `--sidecar` is enabled (default), a JSON file is written alongside each processed file:

```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "file_name": "artwork.pdf",
  "profile_id": "gwg-sheetfed",
  "passed": false,
  "summary": {
    "aground_count": 2,
    "squall_count": 1,
    "advisory_count": 3,
    "total_findings": 6
  },
  "findings": [
    {
      "inspection_id": "GRD_FONT_001",
      "severity": "aground",
      "message": "Font not embedded: Helvetica",
      "page_num": 1
    }
  ],
  "processed_at": "2025-03-22T10:15:30Z"
}
```

## Supported File Types

The hot folder watches for these extensions:

- `.pdf` — PDF documents
- `.eps` — Encapsulated PostScript
- `.ps` — PostScript
- `.tiff`, `.tif` — TIFF images
- `.jpg`, `.jpeg` — JPEG images
- `.png` — PNG images
- `.ai` — Adobe Illustrator

## File Stabilization

Before submitting, the tool verifies the file is fully written by checking that the file size is stable for the configured stabilization period (default: 2 seconds). This prevents submitting partially-copied files.

Increase `--stabilization` for slow network mounts (NFS, SMB):

```bash
lintpdf-watch --watch-dir /mnt/nas/incoming --stabilization 10
```

## Graceful Shutdown

Press `Ctrl+C` or send `SIGTERM` to shut down cleanly. The tool will:

1. Stop watching for new files
2. Finish processing the current file (if any)
3. Exit

Files in the watch directory that haven't been submitted yet are left in place — they'll be picked up on the next start.

## Use Cases

### Prepress Hotfolder Integration

Many prepress systems use hotfolder-based workflows. Place the LintPDF hot folder upstream:

```
[Designer drops PDF] → /hotfolder/incoming
    ↓
[LintPDF hot folder watches]
    ↓
[Passed?]
    ├── Yes → /hotfolder/approved → [Prepress workflow picks up]
    └── No  → /hotfolder/rejected → [Designer notified]
```

### ERP/MIS Output Processing

If your ERP exports artwork files to a directory:

```bash
lintpdf-watch \
  --watch-dir /erp/artwork-export \
  --pass-dir /prepress/ready \
  --fail-dir /erp/needs-review \
  --error-dir /erp/errors \
  --profile gwg-sheetfed
```

### Multiple Profiles

Run multiple instances for different workflows:

```bash
# Offset jobs
lintpdf-watch --watch-dir /jobs/offset --profile gwg-sheetfed --pass-dir /approved/offset &

# Digital jobs
lintpdf-watch --watch-dir /jobs/digital --profile gwg-digital --pass-dir /approved/digital &
```

## Tips

- **Rate limits:** The hot folder respects LintPDF rate limits. If you hit a 429 response, it backs off automatically using the `Retry-After` header.
- **Disk space:** Ensure your pass/fail/error directories have enough disk space. The tool moves (not copies) files.
- **Monitoring:** Use `--log-level DEBUG` to see detailed processing information. In production, pipe logs to a file or log aggregator.
- **Startup:** On startup, the tool processes files already present in the watch directory. To avoid this, ensure the directory is empty before starting.
