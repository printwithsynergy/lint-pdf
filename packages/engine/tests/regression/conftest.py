"""Shared fixtures for regression tests."""

from __future__ import annotations


def pytest_addoption(parser):
    """Register --update-snapshots for the EPM corpus regression."""
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Refresh per-fixture golden snapshots in-place.",
    )
