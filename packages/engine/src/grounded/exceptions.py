"""LintPDF exception hierarchy.

All LintPDF-specific exceptions inherit from GroundedError.
Parser exceptions map to specific failure modes during PDF parsing.
Validation exceptions cover semantic and rule engine issues.
"""


class GroundedError(Exception):
    """Base exception for all LintPDF errors."""


# --- Parser Layer Exceptions ---


class PDFStructureError(GroundedError):
    """PDF file structure is invalid or unreadable.

    Raised when the PDF cannot be opened at all — missing header,
    corrupt xref table, invalid trailer, etc.
    """


class PDFParseError(GroundedError):
    """PDF parsing failed for a specific object or stream.

    Raised when a specific PDF object cannot be parsed, but the
    overall file structure is valid.
    """


class PDFStreamEncodingError(GroundedError):
    """Content stream decompression or decoding failed.

    Raised when a stream filter (FlateDecode, ASCII85Decode, etc.)
    cannot decode the stream data.
    """


class PDFObjectNotFoundError(GroundedError):
    """Requested PDF object does not exist.

    Raised when an indirect reference points to a non-existent object,
    or a required dictionary key is missing.
    """


# --- Semantic Layer Exceptions ---


class InvalidBoxError(GroundedError):
    """Page box coordinates are invalid.

    Raised when box coordinates fail validation (e.g., x0 >= x1)
    or box hierarchy is violated (e.g., TrimBox outside MediaBox).
    """


class InvalidPageError(GroundedError):
    """Page is missing required properties.

    Raised when MediaBox is missing from the page and all ancestors,
    or other required page-level properties cannot be resolved.
    """


class ContentStreamError(GroundedError):
    """Content stream interpretation failed.

    Raised when the content stream interpreter encounters an
    unrecoverable error (e.g., severely malformed operator sequence).
    Non-fatal issues emit warnings instead.
    """


# --- Rule Engine Exceptions ---


class VoyagePlanValidationError(GroundedError):
    """Voyage Plan JSON schema validation failed.

    Raised when a Voyage Plan file does not conform to the
    expected JSON schema.
    """


class RuleRegistrationError(GroundedError):
    """Rule registration failed.

    Raised when a rule function cannot be registered — duplicate name,
    missing analyzer dependency, invalid decorator usage, etc.
    """


class ProfileNotFoundError(GroundedError):
    """Requested Voyage Plan profile does not exist.

    Raised when a profile_id is not found in the ProfileRegistry.
    """


# --- API Layer Exceptions ---


class TenantNotFoundError(GroundedError):
    """Tenant could not be resolved from API key.

    Raised when the provided API key does not map to any tenant.
    """


class RateLimitExceededError(GroundedError):
    """Tenant has exceeded their rate limit.

    Raised when a tenant's request rate exceeds their plan's limit.
    """


class JobNotFoundError(GroundedError):
    """Inspection job not found.

    Raised when a job_id does not exist in the database.
    """
