"""Seed ``system_profiles`` from the bundled JSON directory.

Called once at engine startup (after ``alembic upgrade head``) to
import every ``packages/engine/src/lintpdf/profiles/builtin/*.json``
file into the ``system_profiles`` table.

Semantics — **insert-if-absent**. Once a row exists for a
``profile_id`` it's authoritative; a dev modifying the bundled JSON
for that ID will not propagate to this deployment. New ``profile_id``s
added in the bundled directory (e.g. shipping a new ``ecg-cmyk``
preset alongside an engine deploy) DO get picked up because the row
doesn't exist yet.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from lintpdf.api.models import SystemProfile

_BUILTIN_DIR = Path(__file__).parent / "builtin"

logger = logging.getLogger(__name__)


def seed_system_profiles_from_bundled(db: Session) -> tuple[int, int]:
    """Insert any bundled JSON presets missing from ``system_profiles``.

    Returns ``(inserted, skipped)`` counts so callers can log the
    outcome — useful when debugging "why doesn't my new bundled preset
    appear?" (answer: a row with that profile_id already exists and
    the DB is authoritative, same as admin edits).
    """
    if not _BUILTIN_DIR.is_dir():
        logger.warning(
            "seed_system_profiles_from_bundled: bundled directory missing at %s",
            _BUILTIN_DIR,
        )
        return (0, 0)

    existing: set[str] = {
        row.profile_id for row in db.query(SystemProfile.profile_id).all()
    }

    inserted = 0
    skipped = 0
    for path in sorted(_BUILTIN_DIR.glob("*.json")):
        profile_id = path.stem
        if profile_id in existing:
            skipped += 1
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            logger.exception(
                "seed_system_profiles_from_bundled: failed to parse %s", path
            )
            continue

        # The bundled JSON carries its own "version" field inside the
        # PreflightProfile schema. Snapshot it on the row so future
        # reconciliation tooling can detect drift against the current
        # repo version without re-parsing the JSON blob.
        version = str(data.get("version") or "") or None

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

    if inserted:
        db.commit()
    logger.info(
        "seed_system_profiles_from_bundled: inserted %d, skipped %d (already in DB)",
        inserted,
        skipped,
    )
    return (inserted, skipped)
