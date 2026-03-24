"""Scaffold smoke tests — verify project structure and imports."""

from pathlib import Path


def test_lintpdf_importable() -> None:
    """Verify the lintpdf package can be imported."""
    import lintpdf

    assert lintpdf.__version__ == "0.1.0"


def test_exceptions_importable() -> None:
    """Verify all exception classes are importable."""
    from lintpdf.exceptions import (
        ContentStreamError,
        GroundedError,
        InvalidBoxError,
        InvalidPageError,
        JobNotFoundError,
        PDFObjectNotFoundError,
        PDFParseError,
        PDFStreamEncodingError,
        PDFStructureError,
        ProfileNotFoundError,
        RateLimitExceededError,
        RuleRegistrationError,
        TenantNotFoundError,
        PreflightProfileValidationError,
    )

    # All exceptions inherit from GroundedError
    assert issubclass(PDFStructureError, GroundedError)
    assert issubclass(PDFParseError, GroundedError)
    assert issubclass(PDFStreamEncodingError, GroundedError)
    assert issubclass(PDFObjectNotFoundError, GroundedError)
    assert issubclass(InvalidBoxError, GroundedError)
    assert issubclass(InvalidPageError, GroundedError)
    assert issubclass(ContentStreamError, GroundedError)
    assert issubclass(PreflightProfileValidationError, GroundedError)
    assert issubclass(RuleRegistrationError, GroundedError)
    assert issubclass(ProfileNotFoundError, GroundedError)
    assert issubclass(TenantNotFoundError, GroundedError)
    assert issubclass(RateLimitExceededError, GroundedError)
    assert issubclass(JobNotFoundError, GroundedError)

    # GroundedError inherits from Exception
    assert issubclass(GroundedError, Exception)


def test_exception_instantiation() -> None:
    """Verify exceptions can be raised and caught."""
    from lintpdf.exceptions import GroundedError, PDFStructureError

    try:
        raise PDFStructureError("Test error message")
    except GroundedError as e:
        assert str(e) == "Test error message"
        assert isinstance(e, PDFStructureError)


def test_subpackages_importable() -> None:
    """Verify all subpackage __init__.py files exist and import."""
    import lintpdf.analyzers
    import lintpdf.api
    import lintpdf.conformance
    import lintpdf.parser
    import lintpdf.profiles
    import lintpdf.queue
    import lintpdf.reports
    import lintpdf.rules
    import lintpdf.semantic
    import lintpdf.tenants
    import lintpdf.webhooks

    # Verify these are actual packages (have __path__)
    assert hasattr(lintpdf.parser, "__path__")
    assert hasattr(lintpdf.semantic, "__path__")
    assert hasattr(lintpdf.analyzers, "__path__")
    assert hasattr(lintpdf.api, "__path__")
    assert hasattr(lintpdf.conformance, "__path__")
    assert hasattr(lintpdf.profiles, "__path__")
    assert hasattr(lintpdf.queue, "__path__")
    assert hasattr(lintpdf.reports, "__path__")
    assert hasattr(lintpdf.rules, "__path__")
    assert hasattr(lintpdf.tenants, "__path__")
    assert hasattr(lintpdf.webhooks, "__path__")


def test_project_structure() -> None:
    """Verify expected directory structure exists."""
    src_root = Path(__file__).parent.parent / "src" / "lintpdf"
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
    from lintpdf.api.app import create_app

    app = create_app()
    assert app.title == "LintPDF"
