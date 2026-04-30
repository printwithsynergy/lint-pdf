"""AI accuracy audit — second-pass verification of preflight findings.

Two surfaces:

* :mod:`siftpdf.audit.internal` — Claude Opus 4.7 vision pass. Dev /
  QA only; never runs in the customer request path. Used by the
  admin health toolbox + the golden-PDF harness at
  ``scripts/audit_preflight_accuracy.py`` to red-team the engine
  against a curated corpus.
* :mod:`siftpdf.audit.claude` — Claude Haiku 4.5 customer auditor.
  Runs after ``run_preflight`` when the tenant has ``"audit"`` in
  ``entitlements.ai_features`` (gated behind ``ai_enabled``).
  Populates ``JobFinding.audit_*`` columns inline.

Both auditors return lists of :class:`AuditResult` aligned 1-to-1
with the input findings. Empty / unaudited findings carry a ``None``
status; those rows leave the DB columns NULL and the viewer shows
no chip.
"""

from __future__ import annotations

from siftpdf.audit.types import AuditResult, AuditStatus

__all__ = ["AuditResult", "AuditStatus"]
