"""Universal per-call override envelope.

See ``envelope.py`` for the schema and ``resolver.py`` for the merge
engine. Both submit and mint endpoints accept the same ``OverridesEnvelope``
shape.
"""

from lintpdf.overrides.envelope import (
    AIOverrides,
    BrandingOverridesEnvelope,
    ChecksOverrides,
    ColorOverrides,
    OverridesEnvelope,
    ReportOverrides,
    ShareOverrides,
    ViewerOverrides,
)
from lintpdf.overrides.resolver import (
    EntitlementDenied,
    apply_profile_overrides,
    enforce_report_entitlements,
    viewer_overrides_to_dict,
)

__all__ = [
    "AIOverrides",
    "BrandingOverridesEnvelope",
    "ChecksOverrides",
    "ColorOverrides",
    "EntitlementDenied",
    "OverridesEnvelope",
    "ReportOverrides",
    "ShareOverrides",
    "ViewerOverrides",
    "apply_profile_overrides",
    "enforce_report_entitlements",
    "viewer_overrides_to_dict",
]
