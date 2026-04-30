"""Scaffold smoke tests — verify project structure and imports."""

from pathlib import Path


def test_lintpdf_importable() -> None:
    """Verify the lintpdf package can be imported."""
    import siftpdf

    assert siftpdf.__version__ == "0.1.0"


def test_exceptions_importable() -> None:
    """Verify all exception classes are importable."""
    from siftpdf.exceptions import (
        ContentStreamError,
        InvalidBoxError,
        InvalidPageError,
        JobNotFoundError,
        LintPDFError,
        PDFObjectNotFoundError,
        PDFParseError,
        PDFStreamEncodingError,
        PDFStructureError,
        PreflightProfileValidationError,
        ProfileNotFoundError,
        RateLimitExceededError,
        RuleRegistrationError,
        TenantNotFoundError,
    )

    # All exceptions inherit from LintPDFError
    assert issubclass(PDFStructureError, LintPDFError)
    assert issubclass(PDFParseError, LintPDFError)
    assert issubclass(PDFStreamEncodingError, LintPDFError)
    assert issubclass(PDFObjectNotFoundError, LintPDFError)
    assert issubclass(InvalidBoxError, LintPDFError)
    assert issubclass(InvalidPageError, LintPDFError)
    assert issubclass(ContentStreamError, LintPDFError)
    assert issubclass(PreflightProfileValidationError, LintPDFError)
    assert issubclass(RuleRegistrationError, LintPDFError)
    assert issubclass(ProfileNotFoundError, LintPDFError)
    assert issubclass(TenantNotFoundError, LintPDFError)
    assert issubclass(RateLimitExceededError, LintPDFError)
    assert issubclass(JobNotFoundError, LintPDFError)

    # LintPDFError inherits from Exception
    assert issubclass(LintPDFError, Exception)


def test_exception_instantiation() -> None:
    """Verify exceptions can be raised and caught."""
    from siftpdf.exceptions import LintPDFError, PDFStructureError

    try:
        raise PDFStructureError("Test error message")
    except LintPDFError as e:
        assert str(e) == "Test error message"
        assert isinstance(e, PDFStructureError)


def test_subpackages_importable() -> None:
    """Verify all subpackage __init__.py files exist and import."""
    import siftpdf.analyzers
    import siftpdf.api
    import siftpdf.conformance
    import siftpdf.parser
    import siftpdf.profiles
    import siftpdf.queue
    import siftpdf.reports
    import siftpdf.rules
    import siftpdf.semantic
    import siftpdf.tenants
    import siftpdf.webhooks

    # Verify these are actual packages (have __path__)
    assert hasattr(siftpdf.parser, "__path__")
    assert hasattr(siftpdf.semantic, "__path__")
    assert hasattr(siftpdf.analyzers, "__path__")
    assert hasattr(siftpdf.api, "__path__")
    assert hasattr(siftpdf.conformance, "__path__")
    assert hasattr(siftpdf.profiles, "__path__")
    assert hasattr(siftpdf.queue, "__path__")
    assert hasattr(siftpdf.reports, "__path__")
    assert hasattr(siftpdf.rules, "__path__")
    assert hasattr(siftpdf.tenants, "__path__")
    assert hasattr(siftpdf.webhooks, "__path__")


def test_project_structure() -> None:
    """Verify expected directory structure exists."""
    src_root = Path(__file__).parent.parent / "src" / "siftpdf"
    expected_dirs = [
        "parser",
        "semantic",
        "analyzers",
        "conformance",
        "rules",
        "rules/builtin",
        "profiles",
        "profiles/builtin",
        "reports",
        "reports/templates",
        "api",
        "api/routes",
        "queue",
        "tenants",
        "webhooks",
    ]
    for dir_name in expected_dirs:
        dir_path = src_root / dir_name
        assert dir_path.is_dir(), f"Missing directory: {dir_path}"
        init_path = dir_path / "__init__.py"
        assert init_path.exists(), f"Missing __init__.py: {init_path}"


def test_minimal_pdf_fixture(minimal_pdf_bytes: bytes) -> None:
    """Verify minimal PDF fixture is valid PDF bytes."""
    assert minimal_pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in minimal_pdf_bytes
    assert b"/MediaBox" in minimal_pdf_bytes


def test_api_app_creates() -> None:
    """Verify FastAPI app can be created."""
    from siftpdf.api.app import create_app

    app = create_app()
    assert app.title == "LintPDF"
