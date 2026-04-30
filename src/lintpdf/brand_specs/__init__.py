"""BrandSpec resolver + helpers.

BrandSpec resolution is the logic that, given a job in flight,
picks the single BrandSpec row whose color constraints apply.
See :mod:`lintpdf.brand_specs.resolver` for the rules.
"""

from __future__ import annotations

from lintpdf.brand_specs.resolver import (
    ResolvedBrandSpec,
    resolve_brand_spec_for_job,
    resolve_brand_spec_for_tenant,
)

__all__ = [
    "ResolvedBrandSpec",
    "resolve_brand_spec_for_job",
    "resolve_brand_spec_for_tenant",
]
