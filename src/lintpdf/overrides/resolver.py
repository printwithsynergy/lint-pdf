"""Override resolver — layers overrides onto a profile / viewer config.

Two public entry points:

* :func:`apply_profile_overrides` returns a new ``PreflightProfile`` with
  the caller's ``checks``, ``thresholds``, ``conformance``, ``workflow``,
  ``color``, and ``ai`` overrides applied on top. The orchestrator calls
  this once at job start — the downstream pipeline only sees the merged
  profile, so every analyzer / conformance validator naturally honours the
  overrides without each of them growing an "if override is present"
  branch.

* :func:`enforce_report_entitlements` takes a ``ReportOverrides`` plus the
  tenant's ``TenantEntitlements`` and either returns the sanitised fields
  or raises :class:`EntitlementDenied` (HTTP 403 from the route layer).
  This is the one place plan-gating lives so adding a new overridable
  field doesn't spread gate-logic.

Viewer overrides are shallow dict merges handled inline in the viewer
config endpoint — see :func:`viewer_overrides_to_dict`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lintpdf.overrides.envelope import (
        OverridesEnvelope,
        ReportOverrides,
        ViewerOverrides,
    )
    from lintpdf.profiles.schema import PreflightProfile
    from lintpdf.tenants.entitlements import TenantEntitlements


class EntitlementDenied(Exception):  # noqa: N818 — public API, renaming breaks callers
    """Raised when an override requests something outside the tenant's plan.

    The route layer converts this to HTTP 403 with the message intact so
    the caller sees *exactly* which override got rejected.
    """


# ---------------------------------------------------------------------------
# Profile overrides
# ---------------------------------------------------------------------------


def apply_profile_overrides(
    profile: PreflightProfile,
    overrides: OverridesEnvelope | None,
) -> PreflightProfile:
    """Return a new profile with overrides merged in.

    Override precedence (highest wins): overrides > profile defaults. Only
    non-``None`` override values take effect — you never need to echo back
    the profile's own values to keep them.

    Mutations are scoped to the fields the resolver understands; anything
    not covered here passes through unchanged. That way the orchestrator
    continues to treat the resulting profile as a normal
    :class:`PreflightProfile` — no special-case code.
    """
    if overrides is None:
        return profile

    updates: dict[str, Any] = {}

    # --- top-level scalars ---
    if overrides.conformance is not None:
        updates["conformance"] = overrides.conformance or None
    if overrides.workflow is not None:
        updates["workflow"] = overrides.workflow

    # --- checks ---
    if overrides.checks is not None:
        checks = profile.checks.model_copy(deep=True)
        if overrides.checks.enabled is not None:
            checks.enabled = list(overrides.checks.enabled)
        if overrides.checks.disabled is not None:
            checks.disabled = list(overrides.checks.disabled)
        if overrides.checks.severity_overrides is not None:
            merged = dict(checks.severity_overrides or {})
            merged.update(overrides.checks.severity_overrides)
            checks.severity_overrides = merged
        if overrides.checks.max_severity is not None:
            # Empty string explicitly clears the profile-level cap.
            checks.max_severity = overrides.checks.max_severity or None
        updates["checks"] = checks

    # --- thresholds (arbitrary dict — ThresholdConfig handles validation) ---
    if overrides.thresholds:
        from lintpdf.profiles.schema import ThresholdConfig

        merged_thresh = profile.thresholds.model_dump()
        # ThresholdConfig has explicit fields — drop unknown keys so a
        # typo doesn't get silently persisted as a bogus attribute.
        known = set(ThresholdConfig.model_fields.keys())
        merged_thresh.update({k: v for k, v in overrides.thresholds.items() if k in known})
        updates["thresholds"] = ThresholdConfig(**merged_thresh)

    # --- color ---
    if overrides.color is not None:
        color = profile.color.model_copy(deep=True)
        if overrides.color.target_output_condition is not None:
            color.target_condition = overrides.color.target_output_condition
        if overrides.color.gamut_check is not None:
            color.gamut_check = overrides.color.gamut_check
        if overrides.color.epm_mode is not None:
            color.epm_mode = overrides.color.epm_mode
        if overrides.color.tac_limit is not None:
            color.tac_threshold = overrides.color.tac_limit
        updates["color"] = color

        # Threshold-side fields so analyzers that read ``profile.thresholds``
        # (rather than ``profile.color``) also honour the override.
        from lintpdf.profiles.schema import ThresholdConfig

        thresh = updates.get("thresholds") or profile.thresholds
        thresh_updates: dict[str, Any] = {}
        if overrides.color.target_output_condition is not None:
            thresh_updates["target_output_condition"] = overrides.color.target_output_condition
        if overrides.color.gamut_check is not None:
            thresh_updates["gamut_check"] = overrides.color.gamut_check
        if overrides.color.epm_mode is not None:
            thresh_updates["epm_mode"] = overrides.color.epm_mode
        if overrides.color.ecg_mode is not None:
            thresh_updates["ecg_mode"] = overrides.color.ecg_mode
        if overrides.color.tac_limit is not None:
            thresh_updates["tac_limit"] = overrides.color.tac_limit
        if thresh_updates:
            updates["thresholds"] = ThresholdConfig(**{**thresh.model_dump(), **thresh_updates})

    # --- AI ---
    if overrides.ai is not None:
        ai = profile.ai.model_copy(deep=True)
        if overrides.ai.enabled is not None:
            ai.enabled = overrides.ai.enabled
        if overrides.ai.categories is not None:
            ai.categories = list(overrides.ai.categories)
        if overrides.ai.features is not None:
            ai.features = list(overrides.ai.features)
        if overrides.ai.language_for_reports is not None:
            ai.language_for_reports = overrides.ai.language_for_reports
        # ``preset`` is expanded by the route layer before reaching here
        # — the resolver sees the concrete feature list that came out of
        # the preset. Accepting preset at this layer would duplicate the
        # preset expansion code that lives in routes/jobs.py.
        updates["ai"] = ai

    if not updates:
        return profile
    return profile.model_copy(update=updates)


# ---------------------------------------------------------------------------
# Report overrides — plan-gated
# ---------------------------------------------------------------------------


def enforce_report_entitlements(
    overrides: ReportOverrides | None,
    entitlements: TenantEntitlements,
) -> ReportOverrides | None:
    """Validate report overrides against tenant plan.

    The only plan-gate at the report layer today is
    ``allowed_report_formats`` — tighter formats (``annotated_pdf*``)
    require Scale / Enterprise. Other fields (detail level, summary
    page, expiry, email_to, footer text) are tuning knobs on the
    tenant's own content and have no plan gate. Additional gates can
    be layered in here without touching route code.

    Raises ``EntitlementDenied`` if any gate trips; returns the input
    unchanged otherwise.
    """
    if overrides is None:
        return None

    if overrides.formats is not None:
        allowed = set(entitlements.allowed_report_formats)
        disallowed = [fmt for fmt in overrides.formats if fmt not in allowed]
        if disallowed:
            raise EntitlementDenied(
                "Your plan does not include report format(s): "
                f"{', '.join(sorted(set(disallowed)))}. "
                f"Allowed formats: {', '.join(sorted(allowed))}."
            )

    return overrides


# ---------------------------------------------------------------------------
# Viewer overrides — passed as a dict so the viewer route can merge them
# over its response dict without import-cycle juggling.
# ---------------------------------------------------------------------------


def viewer_overrides_to_dict(overrides: ViewerOverrides | None) -> dict[str, Any]:
    """Return only the non-``None`` fields from a ViewerOverrides.

    Used by the viewer config route after it's built its response dict
    from the tenant / BrandProfile / defaults — we dict-update the
    response so each provided field replaces the resolved value.
    """
    if overrides is None:
        return {}
    return {
        key: value
        for key, value in overrides.model_dump(exclude_unset=True).items()
        if value is not None
    }
