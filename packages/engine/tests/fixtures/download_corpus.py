"""Download test corpus files for LintPDF regression testing.

Downloads PDF test files from various sources:
- veraPDF test suite (PDF/A validation corpus)
- Isartor test suite (deliberately malformed PDFs)
- GWG test files (print preflight scenarios)

Usage:
    python tests/fixtures/download_corpus.py

Files are saved to tests/corpus/ which is gitignored.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import httpx

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

# Test corpus sources
# Each entry: (url, filename, expected_sha256 or None)
CORPUS_FILES: list[tuple[str, str, str | None]] = [
    # veraPDF test suite — PDF/A validation
    (
        "https://github.com/veraPDF/veraPDF-corpus/raw/main/PDF_A-1b/6.1%20File%20structure/6.1.2%20File%20header/veraPDF%20test%20suite%206-1-2-t01-pass-a.pdf",
        "verapdf/pdfa-1b-pass.pdf",
        None,
    ),
    (
        "https://github.com/veraPDF/veraPDF-corpus/raw/main/PDF_A-1b/6.1%20File%20structure/6.1.2%20File%20header/veraPDF%20test%20suite%206-1-2-t01-fail-a.pdf",
        "verapdf/pdfa-1b-fail.pdf",
        None,
    ),
    # Isartor test suite — deliberately invalid PDFs
    (
        "https://www.pdfa.org/wp-content/uploads/2011/08/isartor-6-1-2-t01-fail-a.pdf",
        "isartor/isartor-6-1-2-t01-fail-a.pdf",
        None,
    ),
]


def download_file(url: str, dest: Path) -> bool:
    """Download a file from URL to destination path.

    Returns True if download succeeded, False otherwise.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        print(f"  [skip] {dest.name} already exists")
        return True

    try:
        print(f"  [download] {dest.name} ...", end=" ", flush=True)
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            response = client.get(url)
            response.raise_for_status()
            dest.write_bytes(response.content)
            size_kb = len(response.content) / 1024
            print(f"OK ({size_kb:.1f} KB)")
            return True
    except (httpx.HTTPError, OSError) as e:
        print(f"FAILED ({e})")
        return False


def verify_checksum(path: Path, expected_sha256: str) -> bool:
    """Verify file SHA-256 checksum."""
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    return actual == expected_sha256


def main() -> int:
    """Download all corpus files."""
    print(f"Downloading test corpus to {CORPUS_DIR}/\n")

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for url, filename, expected_hash in CORPUS_FILES:
        dest = CORPUS_DIR / filename
        if download_file(url, dest):
            if expected_hash and not verify_checksum(dest, expected_hash):
                print(f"  [WARN] Checksum mismatch for {filename}")
                fail_count += 1
            else:
                success_count += 1
        else:
            fail_count += 1

    print(f"\nDone: {success_count} downloaded, {fail_count} failed")
    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
