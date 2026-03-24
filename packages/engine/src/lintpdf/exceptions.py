"""LintPDF exception hierarchy.

All LintPDF-specific exceptions inherit from LintPDFError.
Parser exceptions map to specific failure modes during PDF parsing.
Validation exceptions cover semantic and rule engine issues.
"""


class LintPDFError(Exception):
    """Base exception for all LintPDF errors."""


# Backwards compatibility alias
GroundedError = LintPDFError


# --- Parser Layer Exceptions ---


class PDFStructureError(LintPDFError):
    """PDF file structure is invalid or unreadable.

    Raised when the PDF cannot be opened at all — missing header,
    corrupt xref table, invalid trailer, etc.
    """


class PDFParseError(LintPDFError):
    """PDF parsing failed for a specific object or stream.

    Raised when a specific PDF object cannot be parsed, but the
    overall file structure is valid.
    """


class PDFStreamEncodingError(LintPDFError):
    """Content stream decompression or decoding failed.

    Raised when a stream filter (FlateDecode, ASCII85Decode, etc.)
    cannot decode the stream data.
    """


class PDFObjectNotFoundError(LintPDFError):
    """Requested PDF object does not exist.

    Raised when an indirect reference points to a non-existent object,
    or a required dictionary key is missing.
    """


# --- Semantic Layer Exceptions ---


class InvalidBoxError(LintPDFError):
    """Page box coordinates are invalid.

    Raised when box coordinates fail validation (e.g., x0 >= x1)
    or box hierarchy is violated (e.g., TrimBox outside MediaBox).
    """


class InvalidPageError(LintPDFError):
    """Page is missing required properties.

    Raised when MediaBox is missing from the page and all ancestors,
    or other required page-level properties cannot be resolved.
    """


class ContentStreamError(LintPDFError):
    """Content stream interpretation failed.

    Raised when the content stream interpreter encounters an
    unrecoverable error (e.g., severely malformed operator sequence).
    Non-fatal issues emit warnings instead.
    """


# --- Rule Engine Exceptions ---


class PreflightProfileValidationError(LintPDFError):
    """Preflight Profile JSON schema validation failed.

    Raised when a Preflight Profile does not conform to the
    expected JSON schema.
    """


# Backwards compatibility alias
VoyagePlanValidationError = PreflightProfileValidationError


class RuleRegistrationError(LintPDFError):
    """Rule registration failed.

    Raised when a rule function cannot be registered — duplicate name,
    missing analyzer dependency, invalid decorator usage, etc.
    """


class ProfileNotFoundError(LintPDFError):
    """Requested preflight profile does not exist.

    Raised when a profile_id is not found in the ProfileRegistry.
    """


# --- API Layer Exceptions ---


class TenantNotFoundError(LintPDFError):
    """Tenant could not be resolved from API key.

    Raised when the provided API key does not map to any tenant.
    """


class RateLimitExceededError(LintPDFError):
    """Tenant has exceeded their rate limit.

    Raised when a tenant's request rate exceeds their plan's limit.
    """


class JobNotFoundError(LintPDFError):
    """Inspection job not found.

    Raised when a job_id does not exist in the database.
    """
