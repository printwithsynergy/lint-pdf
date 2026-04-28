"""Q-C2 / Q-C3 / Q-C7 — EPM candidacy substrate.

Enhanced Productivity Mode is the HP Indigo "CMY-only" workflow: the
press skips the K plate to gain ~30% throughput. Routing a job into
EPM is only worthwhile when the artwork can survive the loss of the
K channel without colour shifts, density loss, or spot fidelity
problems. This package owns:

* ``codes`` — the 16 ``LPDF_EPM_*_REJECT`` inspection IDs newly added
  by Q-C7 to cover the EPM-A/B/C v2-universe checks not already
  present in the legacy ``LPDF_EPM_001..018`` set.
* ``scoring`` — a deterministic scorer that takes a list of fired
  EPM-tier findings and decides whether the job is EPM-eligible,
  EPM-marginal, or EPM-rejected. Mirrors the playbook §2.EPM.x
  decision tree.
* ``thresholds`` — the Q-C2 rich-black recipe + Q-C3 coated-default
  TAC limits, surfaced as the registry default for the
  ``epm_thresholds`` toggle.

This module is purely metadata + scoring. The analyzer modules that
fire the findings live in ``lintpdf.analyzers`` and ``lintpdf.ai``.
"""
