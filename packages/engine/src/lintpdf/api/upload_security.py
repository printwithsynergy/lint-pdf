"""Centralized file upload validation and security.

Provides magic-bytes detection, filename sanitization, double-extension
attack prevention, SVG safety validation, and optional ClamAV virus scanning.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from typing import IO, TYPE_CHECKING

import clamd as _clamd_mod
import defusedxml.ElementTree as DefusedET
import filetype as filetype_lib
from fastapi import HTTPException, UploadFile, status

if TYPE_CHECKING:
    from lintpdf.api.config import Settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File type registry
# ---------------------------------------------------------------------------

_DETECTION_FILETYPE = "filetype"
_DETECTION_CUSTOM = "custom"
_DETECTION_EXTENSION_ONLY = "extension_only"


@dataclass(frozen=True)
class AllowedFileType:
    """Defines an allowed file type with MIME, extensions, and detection strategy."""

    mime_type: str
    extensions: frozenset[str]
    detection: str = _DETECTION_FILETYPE  # "filetype" | "custom" | "extension_only"


# --- Tier 1: detected by the filetype library ---
_PNG = AllowedFileType("image/png", frozenset({".png"}))
_JPEG = AllowedFileType("image/jpeg", frozenset({".jpg", ".jpeg"}))
_TIFF = AllowedFileType("image/tiff", frozenset({".tif", ".tiff"}))
_WEBP = AllowedFileType("image/webp", frozenset({".webp"}))
_GIF = AllowedFileType("image/gif", frozenset({".gif"}))
_PDF = AllowedFileType("application/pdf", frozenset({".pdf"}))
_PSD = AllowedFileType("image/vnd.adobe.photoshop", frozenset({".psd"}))

# --- Tier 2: custom magic-bytes detection ---
_EPS = AllowedFileType("application/postscript", frozenset({".eps"}), _DETECTION_CUSTOM)
_INDD = AllowedFileType("application/x-indesign", frozenset({".indd"}), _DETECTION_CUSTOM)
_SVG = AllowedFileType("image/svg+xml", frozenset({".svg"}), _DETECTION_CUSTOM)

# --- Tier 3: extension-only (no reliable magic bytes) ---
_QXP = AllowedFileType(
    "application/x-quark-xpress", frozenset({".qxp", ".qxd"}), _DETECTION_EXTENSION_ONLY
)
_JDF = AllowedFileType(
    "application/vnd.cip4-jdf+xml", frozenset({".jdf"}), _DETECTION_EXTENSION_ONLY
)
_XJDF = AllowedFileType(
    "application/vnd.cip4-xjdf+xml", frozenset({".xjdf"}), _DETECTION_EXTENSION_ONLY
)

# Pre-built registries for endpoints
PDF_TYPES: frozenset[AllowedFileType] = frozenset({_PDF})

# Sentinel: accept any extension EXCEPT those in DANGEROUS_EXTENSIONS.
# Used by the public trial endpoint where we want permissive intake but still
# need to block executables/scripts. Magic-bytes and MIME cross-checks are
# skipped for this path — ClamAV is the safety net.
ANY_SAFE_TYPES: frozenset[AllowedFileType] = frozenset()

PRINT_READY_TYPES: frozenset[AllowedFileType] = frozenset(
    {
        _PNG,
        _JPEG,
        _TIFF,
        _WEBP,
        _GIF,
        _PDF,
        _PSD,
        _EPS,
        _INDD,
        _SVG,
        _QXP,
        _JDF,
        _XJDF,
    }
)

# ---------------------------------------------------------------------------
# Dangerous extensions (double-extension attack detection)
# ---------------------------------------------------------------------------

DANGEROUS_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".php",
        ".exe",
        ".sh",
        ".bat",
        ".cmd",
        ".js",
        ".html",
        ".htm",
        ".asp",
        ".aspx",
        ".jsp",
        ".cgi",
        ".py",
        ".pl",
        ".rb",
        ".msi",
        ".com",
        ".scr",
        ".pif",
        ".vbs",
        ".wsf",
        ".ps1",
    }
)

# ---------------------------------------------------------------------------
# SVG safety — elements and attributes that indicate embedded code
# ---------------------------------------------------------------------------

_SVG_DANGEROUS_TAGS: frozenset[str] = frozenset(
    {
        "script",
        "foreignobject",
        "iframe",
        "embed",
        "object",
        "applet",
    }
)

_SVG_EVENT_ATTR_RE = re.compile(r"^on[a-z]", re.IGNORECASE)

_SVG_DANGEROUS_URI_RE = re.compile(r"^\s*(javascript|data)\s*:", re.IGNORECASE)

_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"

# ---------------------------------------------------------------------------
# Custom magic-bytes signatures
# ---------------------------------------------------------------------------

_EPS_ASCII_MAGIC = b"%!PS-Adobe"
_EPS_BINARY_MAGIC = b"\xc5\xd0\xd3\xc6"
_INDD_MAGIC = b"\x06\x06\xed\xf5\xd8\x1d\x46\xe5"


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------


def sanitize_filename(filename: str | None) -> str:
    """Sanitize an upload filename for safe use.

    Strips path components, null bytes, and control characters.
    Raises HTTPException(422) if the filename is empty or invalid.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required.",
        )

    # Strip path components — prevent directory traversal (handles both / and \)
    cleaned = filename.replace("\\", "/")
    cleaned = os.path.basename(cleaned)

    # Remove null bytes
    cleaned = cleaned.replace("\x00", "")

    # Remove control characters (Unicode categories Cc and Cf)
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch) not in ("Cc", "Cf"))

    cleaned = cleaned.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid filename.",
        )

    return cleaned


def _check_double_extension(filename: str) -> None:
    """Reject filenames with dangerous interior extensions.

    For example, ``malware.php.png`` has ``.php`` as an interior segment.
    """
    parts = filename.rsplit(".", maxsplit=10)
    if len(parts) <= 2:
        return  # single extension — nothing to check

    # Check all interior segments (everything except first and last)
    for segment in parts[1:-1]:
        ext = f".{segment.lower()}"
        if ext in DANGEROUS_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Suspicious filename pattern detected.",
            )


# ---------------------------------------------------------------------------
# SVG validation
# ---------------------------------------------------------------------------


def _validate_svg_safety(content: bytes) -> None:
    """Parse SVG with defusedxml and reject if it contains executable content."""
    try:
        tree = DefusedET.fromstring(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SVG file is malformed or contains unsafe XML.",
        ) from exc

    _walk_svg_element(tree)


def _walk_svg_element(element: DefusedET.Element) -> None:
    """Recursively check an SVG element tree for dangerous content."""
    # Strip namespace for tag comparison
    tag = element.tag
    if "}" in tag:
        tag = tag.split("}", 1)[1]

    if tag.lower() in _SVG_DANGEROUS_TAGS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"SVG contains forbidden element: <{tag}>.",
        )

    # Check attributes for event handlers and dangerous URIs
    for attr_name, attr_value in element.attrib.items():
        # Strip namespace from attribute name
        if "}" in attr_name:
            attr_name = attr_name.split("}", 1)[1]

        if _SVG_EVENT_ATTR_RE.match(attr_name):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"SVG contains forbidden event handler: {attr_name}.",
            )

        # Check href/xlink:href for javascript: or data: URIs
        if attr_name.lower() in ("href", "xlink:href") and _SVG_DANGEROUS_URI_RE.match(attr_value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="SVG contains forbidden URI scheme.",
            )

    for child in element:
        _walk_svg_element(child)


# ---------------------------------------------------------------------------
# Custom magic-bytes detection for Tier 2 formats
# ---------------------------------------------------------------------------


def _detect_custom_mime(content: bytes) -> str | None:
    """Detect MIME type for formats not supported by the filetype library."""
    if content[: len(_EPS_ASCII_MAGIC)] == _EPS_ASCII_MAGIC:
        return "application/postscript"
    if content[: len(_EPS_BINARY_MAGIC)] == _EPS_BINARY_MAGIC:
        return "application/postscript"
    if content[: len(_INDD_MAGIC)] == _INDD_MAGIC:
        return "application/x-indesign"

    # SVG detection: try to find an <svg root in what looks like XML
    # Only check the first 4KB to avoid scanning large files
    head = content[:4096]
    try:
        text = head.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None
    # Check for SVG root element in what looks like XML
    if "<svg" in text.lower():
        return "image/svg+xml"

    return None


# ---------------------------------------------------------------------------
# ClamAV malware scanning
# ---------------------------------------------------------------------------


def _scan_with_clamd(scan_input: "BytesIO | IO[bytes]", settings: Settings) -> None:
    """Shared body for both the bytes and streaming scan variants.

    ``scan_input`` is anything ``clamd.instream`` accepts (BytesIO or a
    seekable file-like). Raises HTTPException(422) only on a positive
    detection; every other failure is logged and allows the upload
    through (fail-open) so a broken ClamAV sidecar never takes down
    production. See CLAUDE.md for the fail-open rationale.
    """
    if not settings.clamav_url:
        logger.warning(
            "ClamAV is not configured (LINTPDF_CLAMAV_URL is unset) — "
            "skipping virus scan (fail-open)"
        )
        return
    try:
        host, _, port_str = settings.clamav_url.rpartition(":")
        port = int(port_str) if port_str else 3310
        host = host.strip().strip("[]") or "localhost"
        scanner = _clamd_mod.ClamdNetworkSocket(host=host, port=port, timeout=30)
        result = scanner.instream(scan_input)
    except HTTPException:
        raise
    except Exception:
        logger.warning(
            "ClamAV scan failed — service unreachable at %s; allowing upload (fail-open)",
            settings.clamav_url,
            exc_info=True,
        )
        return
    if result and result.get("stream", ("OK",))[0] == "FOUND":
        virus_name = result["stream"][1]
        logger.warning("Malware detected in upload: %s", virus_name)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File rejected: potential malware detected.",
        )


def scan_for_malware(content: bytes, settings: Settings) -> None:
    """Scan raw file bytes with ClamAV. See ``_scan_with_clamd`` for semantics."""
    _scan_with_clamd(BytesIO(content), settings)


def scan_for_malware_stream(fileobj: "IO[bytes]", settings: Settings) -> None:
    """Scan a seekable file-like with ClamAV.

    Avoids the ~50 MB-per-scan RSS spike that ``scan_for_malware`` takes
    when handed a bytes copy of a big PDF spool. ``clamd.instream``
    natively reads the stream in 64 KB chunks. Caller is responsible
    for seeking ``fileobj`` to byte 0 before and (if they want to reuse
    it) after the call.
    """
    pos = fileobj.tell()
    try:
        _scan_with_clamd(fileobj, settings)
    finally:
        try:
            fileobj.seek(pos)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main validation function
# ---------------------------------------------------------------------------


async def validate_upload(
    file: UploadFile,
    *,
    allowed_types: frozenset[AllowedFileType],
    max_size_bytes: int | None = None,
    settings: Settings | None = None,
) -> bytes:
    """Validate an uploaded file and return its raw bytes.

    Performs filename sanitization, extension validation, magic-bytes
    detection, SVG safety checks, optional size limits, and optional
    ClamAV malware scanning.

    Parameters
    ----------
    file:
        The FastAPI ``UploadFile`` from the request.
    allowed_types:
        Set of ``AllowedFileType`` definitions that this endpoint accepts.
    max_size_bytes:
        Maximum file size in bytes. ``None`` to skip the size check.
    settings:
        Application settings (used for ClamAV URL). ``None`` to skip scanning.

    Returns
    -------
    bytes
        The raw file content, ready for storage.

    Raises
    ------
    HTTPException
        422 for validation failures, 413 for size limit exceeded.
    """
    # 1. Fast size reject — before we read the body into memory.
    #
    # Starlette's ``UploadFile.size`` is populated from Content-Length on
    # multipart uploads; when the client honestly declares a 2 GB file
    # for a 10 MB-cap tenant, we 413 in a few milliseconds without
    # buffering anything. A malicious client that lies about its size
    # (or omits the header) still hits the streaming guard below.
    declared_size = getattr(file, "size", None)
    if max_size_bytes is not None and declared_size is not None and declared_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_mb:.0f} MB.",
        )

    # 2. Stream the body in bounded chunks; abort the moment we exceed
    # ``max_size_bytes``. This caps peak memory at ``max_size_bytes``
    # even when the client lied about (or omitted) Content-Length.
    from lintpdf.api.config import get_settings as _get_upload_settings

    chunk_size = _get_upload_settings().max_upload_stream_chunk_bytes
    buffer = bytearray()
    total = 0
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if max_size_bytes is not None and total > max_size_bytes:
            max_mb = max_size_bytes / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_mb:.0f} MB.",
            )
        buffer.extend(chunk)
    content = bytes(buffer)

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    # 2. Sanitize filename
    clean_name = sanitize_filename(file.filename)

    # 3. Double-extension attack detection
    _check_double_extension(clean_name)

    # 4. Extension validation
    _, ext = os.path.splitext(clean_name)
    ext_lower = ext.lower()

    detected_mime: str | None = None

    if not allowed_types:
        # ANY_SAFE_TYPES path: reject only DANGEROUS_EXTENSIONS, skip magic-bytes
        # and MIME cross-checks — we can't cross-check arbitrary formats.
        if ext_lower in DANGEROUS_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File extension '{ext_lower}' is not allowed.",
            )
    else:
        matching_types = [t for t in allowed_types if ext_lower in t.extensions]
        if not matching_types:
            allowed_exts = sorted({e for t in allowed_types for e in t.extensions})
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File extension '{ext_lower}' is not allowed. "
                f"Allowed: {', '.join(allowed_exts)}",
            )

        # 5. Content detection based on type strategy
        matched_type = matching_types[0]

        if matched_type.detection == _DETECTION_FILETYPE:
            guess = filetype_lib.guess(content)
            detected_mime = guess.mime if guess else None
        elif matched_type.detection == _DETECTION_CUSTOM:
            detected_mime = _detect_custom_mime(content)
        # _DETECTION_EXTENSION_ONLY: skip content check

        # 6. Verify detected MIME matches an allowed type
        if matched_type.detection != _DETECTION_EXTENSION_ONLY:
            if detected_mime is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="File content does not match a supported type.",
                )

            allowed_mimes = {t.mime_type for t in allowed_types}
            if detected_mime not in allowed_mimes:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="File content does not match a supported type.",
                )

            # 7. Cross-check: detected MIME must agree with claimed extension
            extension_mimes = {t.mime_type for t in matching_types}
            if detected_mime not in extension_mimes:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"File content ({detected_mime}) does not match extension ({ext_lower}).",
                )

        # 8. SVG safety validation
        if detected_mime == "image/svg+xml":
            _validate_svg_safety(content)

    # 9. Size limit is enforced during the streaming read above; no
    # additional post-hoc check is required.

    # 10. ClamAV malware scan (if configured)
    if settings is not None:
        scan_for_malware(content, settings)

    return content


# ---------------------------------------------------------------------------
# Streaming variant — spools to disk so we never hold 30-50 MB bodies in RAM.
# Used by the PDF upload hot path (routes/jobs.py, batch.py, trial.py,
# endpoints.py). The legacy ``validate_upload`` stays for small-file routes
# (logo upload, branding icons) where the body already fits in a few KB.
# ---------------------------------------------------------------------------


_SPOOL_RAM_THRESHOLD_BYTES = 4 * 1024 * 1024  # 4 MB spills to disk past this.


async def validate_upload_streaming(
    file: UploadFile,
    *,
    allowed_types: frozenset[AllowedFileType],
    max_size_bytes: int | None = None,
    settings: Settings | None = None,
) -> tuple[IO[bytes], int]:
    """Validate an uploaded file and return a spooled handle + its size.

    Same validation chain as :py:func:`validate_upload` but the body is
    streamed into a :py:class:`tempfile.SpooledTemporaryFile` rather
    than a :py:class:`bytearray`. Small uploads (under the 4 MB spool
    threshold) stay in RAM; larger ones spill to the container's
    ephemeral disk. Either way peak process RSS is bounded by the
    threshold — N concurrent 50 MB uploads no longer OOM the container.

    The caller gets a file-like object, positioned at byte 0, ready to
    hand directly to :py:meth:`StorageBackend.upload_pdf_stream`, plus
    the validated byte length. The caller MUST close the handle
    (``fileobj.close()``) once the upload is queued.

    Validation steps 2-9 that previously operated on the full ``bytes``
    buffer (filename sanitization, magic-bytes detection, SVG safety)
    now read a single head chunk out of the spool and seek back. Full
    content is only re-read for the ClamAV scan (which is still
    bytes-based upstream); in practice the ClamAV read is against the
    on-disk spool so it too avoids RSS pressure.

    Parameters
    ----------
    file:
        The FastAPI ``UploadFile`` from the request.
    allowed_types:
        Set of ``AllowedFileType`` definitions that this endpoint accepts.
    max_size_bytes:
        Maximum file size in bytes. ``None`` to skip the size check.
    settings:
        Application settings (used for ClamAV URL). ``None`` to skip scanning.

    Returns
    -------
    tuple[IO[bytes], int]
        The spooled file handle (positioned at 0) and the total byte count.

    Raises
    ------
    HTTPException
        422 for validation failures, 413 for size limit exceeded.
    """
    # 1. Fast size reject on the declared Content-Length.
    declared_size = getattr(file, "size", None)
    if max_size_bytes is not None and declared_size is not None and declared_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_mb:.0f} MB.",
        )

    # 2. Stream into a spool; abort the moment we exceed max_size_bytes.
    from lintpdf.api.config import get_settings as _get_upload_settings

    chunk_size = _get_upload_settings().max_upload_stream_chunk_bytes
    spool: IO[bytes] = tempfile.SpooledTemporaryFile(
        max_size=_SPOOL_RAM_THRESHOLD_BYTES,
        mode="w+b",
    )
    total = 0
    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if max_size_bytes is not None and total > max_size_bytes:
                max_mb = max_size_bytes / (1024 * 1024)
                spool.close()
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds maximum size of {max_mb:.0f} MB.",
                )
            spool.write(chunk)

        if total == 0:
            spool.close()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded file is empty.",
            )

        # 3. Sanitize filename
        clean_name = sanitize_filename(file.filename)

        # 4. Double-extension attack detection
        _check_double_extension(clean_name)

        # 5. Extension validation
        _, ext = os.path.splitext(clean_name)
        ext_lower = ext.lower()

        detected_mime: str | None = None

        if not allowed_types:
            if ext_lower in DANGEROUS_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"File extension '{ext_lower}' is not allowed.",
                )
        else:
            matching_types = [t for t in allowed_types if ext_lower in t.extensions]
            if not matching_types:
                allowed_exts = sorted({e for t in allowed_types for e in t.extensions})
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"File extension '{ext_lower}' is not allowed. "
                    f"Allowed: {', '.join(allowed_exts)}",
                )

            matched_type = matching_types[0]

            # 6. Content detection — only the first 8 KB is needed for
            # magic-bytes / custom-MIME sniffing on PDFs + SVGs; reading
            # the full spool here would re-load the body we just tried
            # to keep off-heap.
            head_size = 8 * 1024
            spool.seek(0)
            head = spool.read(head_size)
            spool.seek(0)

            if matched_type.detection == _DETECTION_FILETYPE:
                guess = filetype_lib.guess(head)
                detected_mime = guess.mime if guess else None
            elif matched_type.detection == _DETECTION_CUSTOM:
                detected_mime = _detect_custom_mime(head)

            if matched_type.detection != _DETECTION_EXTENSION_ONLY:
                if detected_mime is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="File content does not match a supported type.",
                    )
                allowed_mimes = {t.mime_type for t in allowed_types}
                if detected_mime not in allowed_mimes:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="File content does not match a supported type.",
                    )
                extension_mimes = {t.mime_type for t in matching_types}
                if detected_mime not in extension_mimes:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"File content ({detected_mime}) does not match extension ({ext_lower}).",
                    )

            # 7. SVG safety — SVGs are small; if we see one, read the
            # full spool for the defusedxml parse. PDFs skip this branch.
            if detected_mime == "image/svg+xml":
                spool.seek(0)
                svg_bytes = spool.read()
                spool.seek(0)
                _validate_svg_safety(svg_bytes)

        # 8. ClamAV scan reads the spool in 64 KB chunks via
        # clamd.instream — zero full-body materialization. This is
        # the hot-path fix for the tier-1 wedge on 2026-04-21 where
        # a 50 MB PDF buffered here spiked worker RSS enough to
        # starve /ready health checks.
        if settings is not None:
            spool.seek(0)
            scan_for_malware_stream(spool, settings)
            spool.seek(0)

        # 9. Hand back a seek-to-0 spool plus the size.
        spool.seek(0)
        return spool, total
    except HTTPException:
        try:
            spool.close()
        except Exception:
            pass
        raise
    except Exception:
        try:
            spool.close()
        except Exception:
            pass
        raise
