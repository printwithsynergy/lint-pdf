"""Seed ``system_profiles`` from the bundled JSON directory.

Called once at engine startup (after ``alembic upgrade head``) to
import every ``packages/engine/src/lintpdf/profiles/builtin/*.json``
file into the ``system_profiles`` table.

Semantics:

* **Missing row** — insert from bundled JSON with ``source='bundled'``.
* **Existing bundled row with stale ``bundled_version``** — reconcile
  in place: replace ``preflight_profile_json`` and bump
  ``bundled_version`` to the on-disk value. This is how a profile
  schema change (e.g. adding ``LPDF_*`` / ``AI_*`` to ``checks.enabled``)
  reaches deployments that seeded the row before the change shipped.
* **Existing admin-edited row** (``source != 'bundled'``) — never
  touched. The first PATCH flips ``source`` to ``'admin'`` so the
  operator's intent is sacred.
* **Existing bundled row with matching ``bundled_version``** — no-op.

Authors of bundled JSON MUST bump the top-level ``version`` field
whenever they change ``checks.enabled``, ``thresholds``, or any other
runtime-affecting key — otherwise deployments will never pick up the
new content.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from lintpdf.api.models import SystemProfile

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_BUILTIN_DIR = Path(__file__).parent / "builtin"

logger = logging.getLogger(__name__)


def seed_system_profiles_from_bundled(db: Session) -> tuple[int, int, int]:
    """Insert missing bundled presets and reconcile stale bundled rows.

    Returns ``(inserted, updated, skipped)``. ``updated`` counts
    bundled-source rows whose ``bundled_version`` changed on disk;
    ``skipped`` covers both up-to-date bundled rows and admin-edited
    rows (which are never modified).
    """
    if not _BUILTIN_DIR.is_dir():
        logger.warning(
            "seed_system_profiles_from_bundled: bundled directory missing at %s",
            _BUILTIN_DIR,
        )
        return (0, 0, 0)

    existing_rows: dict[str, SystemProfile] = {
        row.profile_id: row for row in db.query(SystemProfile).all()
    }

    inserted = 0
    updated = 0
    skipped = 0
    for path in sorted(_BUILTIN_DIR.glob("*.json")):
        profile_id = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("seed_system_profiles_from_bundled: failed to parse %s", path)
            continue

        version = str(data.get("version") or "") or None
        row = existing_rows.get(profile_id)

        if row is None:
            db.add(
                SystemProfile(
                    profile_id=profile_id,
                    preflight_profile_json=data,
                    source="bundled",
                    bundled_version=version,
                    visibility_mode="all",
                )
            )
            inserted += 1
            continue

        if row.source != "bundled":
            # Admin edits are authoritative — never overwrite.
            skipped += 1
            continue

        if row.bundled_version == version:
            skipped += 1
            continue

        # Bundled-source row with a different version — reconcile in place.
        row.preflight_profile_json = data
        row.bundled_version = version
        updated += 1
        logger.info(
            "seed_system_profiles_from_bundled: reconciled %s (was %r → %r)",
            profile_id,
            row.bundled_version,
            version,
        )

    if inserted or updated:
        db.commit()
    logger.info(
        "seed_system_profiles_from_bundled: inserted %d, updated %d, skipped %d",
        inserted,
        updated,
        skipped,
    )
    return (inserted, updated, skipped)
