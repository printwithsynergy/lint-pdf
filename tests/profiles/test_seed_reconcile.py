"""Regression tests for ``seed_system_profiles_from_bundled`` reconcile semantics.

Bundled-source rows whose ``bundled_version`` differs from the on-disk
JSON must be replaced in place at next startup. Admin-edited rows
(``source != 'bundled'``) must never be touched.

Background — without reconcile, the demo silently regresses: a deployment
seeded against an older ``lintpdf-default`` (say one whose ``checks.enabled``
only listed ``PDFX4-*``) keeps that stale row forever, so adding ``LPDF_*``
+ ``AI_*`` to the bundled JSON has no effect. See seed.py module docstring
for the full contract.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lintpdf.api.models import Base, SystemProfile
from lintpdf.profiles.seed import seed_system_profiles_from_bundled

_BUILTIN_DIR = Path(__file__).parents[2] / "src" / "lintpdf" / "profiles" / "builtin"


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _current_bundled_version(profile_id: str) -> str:
    data = json.loads((_BUILTIN_DIR / f"{profile_id}.json").read_text(encoding="utf-8"))
    return str(data["version"])


class TestSeedReconcile:
    @staticmethod
    def test_inserts_when_missing(db: Session) -> None:
        inserted, updated, _ = seed_system_profiles_from_bundled(db)
        assert inserted > 0
        assert updated == 0
        # lintpdf-default is one of the bundled profiles; row should now exist.
        row = db.query(SystemProfile).filter_by(profile_id="lintpdf-default").one()
        assert row.source == "bundled"
        assert row.bundled_version == _current_bundled_version("lintpdf-default")

    @staticmethod
    def test_reconciles_bundled_row_with_stale_version(db: Session) -> None:
        """A bundled-source row with an older version must be replaced
        in place — this is the demo-regression fix path."""
        # Seed a deliberately-stale row that omits LPDF_*/AI_* — exactly
        # the failure mode that caused "only PDF validation works" in
        # the demo.
        db.add(
            SystemProfile(
                profile_id="lintpdf-default",
                preflight_profile_json={
                    "name": "Stale",
                    "version": "0.1",
                    "checks": {"enabled": ["PDFX4-*"], "disabled": [], "severity_overrides": {}},
                },
                source="bundled",
                bundled_version="0.1",
                visibility_mode="all",
            )
        )
        db.commit()

        _, updated, _ = seed_system_profiles_from_bundled(db)
        assert updated >= 1

        row = db.query(SystemProfile).filter_by(profile_id="lintpdf-default").one()
        assert row.bundled_version == _current_bundled_version("lintpdf-default")
        # Reconciled JSON must include the print-impacting check patterns
        # the demo depends on (hairline strokes, small text, AI signals).
        enabled = row.preflight_profile_json["checks"]["enabled"]
        assert "LPDF_*" in enabled
        assert "AI_*" in enabled

    @staticmethod
    def test_never_touches_admin_edited_row(db: Session) -> None:
        """Admin edits are sacred — once ``source != 'bundled'`` the
        seeder must not overwrite, even when ``bundled_version`` is stale."""
        admin_payload = {
            "name": "Admin Custom",
            "version": "0.0",
            "checks": {"enabled": ["LPDF_FONT_001"], "disabled": [], "severity_overrides": {}},
        }
        db.add(
            SystemProfile(
                profile_id="lintpdf-default",
                preflight_profile_json=admin_payload,
                source="admin",
                bundled_version="0.0",
                visibility_mode="all",
            )
        )
        db.commit()

        seed_system_profiles_from_bundled(db)

        row = db.query(SystemProfile).filter_by(profile_id="lintpdf-default").one()
        assert row.source == "admin"
        assert row.preflight_profile_json == admin_payload
        # The admin row must not have been counted as an update.
        # (Other bundled rows that were missing still count toward `updated=0`
        # for this specific row — the assertion below is per-row, not total.)
        assert row.bundled_version == "0.0"

    @staticmethod
    def test_idempotent_when_versions_match(db: Session) -> None:
        # First seed.
        seed_system_profiles_from_bundled(db)
        # Second seed — every bundled row already matches, nothing changes.
        inserted, updated, skipped = seed_system_profiles_from_bundled(db)
        assert inserted == 0
        assert updated == 0
        assert skipped > 0
