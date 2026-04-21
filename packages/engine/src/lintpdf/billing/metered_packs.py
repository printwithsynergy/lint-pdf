"""Metered-resource pack catalogue (Python mirror of packages/stripe/src/metered-packs.ts).

Two "kinds" of resources are sold as one-off top-ups alongside the
plan subscription: AI credits and file packs. Each kind has three
fixed-size packs. The Stripe price IDs for both live + sandbox are
hardcoded below and overridable via env vars at runtime.

To add a new pack size, bump this file AND
``packages/stripe/src/metered-packs.ts`` in the same commit so the
dashboard "Buy more" flow and the engine ``/topup`` endpoint agree.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

PackKind = Literal["credits", "files"]


@dataclass(frozen=True)
class PackDef:
    kind: PackKind
    size: int
    usd_cents: int
    price_id_live: str
    price_id_sandbox: str


# IDs minted via packages/stripe/scripts/sync-metered-packs.ts on 2026-04-17.
METERED_PACKS: dict[str, PackDef] = {
    "credits_500": PackDef(
        kind="credits",
        size=500,
        usd_cents=2500,
        price_id_live="price_1TNHg8GdPozm4cl0SO01uMtG",
        price_id_sandbox="price_1TNHfgKIaHHghEpJHwagKqXs",
    ),
    "credits_2000": PackDef(
        kind="credits",
        size=2000,
        usd_cents=9000,
        price_id_live="price_1TNHg9GdPozm4cl0oP7z40Xo",
        price_id_sandbox="price_1TNHfhKIaHHghEpJ4YbG4OsC",
    ),
    "credits_10000": PackDef(
        kind="credits",
        size=10000,
        usd_cents=40000,
        price_id_live="price_1TNHg9GdPozm4cl0GrqMkwlI",
        price_id_sandbox="price_1TNHfhKIaHHghEpJ60lJbmr7",
    ),
    "files_500": PackDef(
        kind="files",
        size=500,
        usd_cents=1500,
        price_id_live="price_1TNHgAGdPozm4cl0vpKicGI3",
        price_id_sandbox="price_1TNHfiKIaHHghEpJl9lhXeFU",
    ),
    "files_2500": PackDef(
        kind="files",
        size=2500,
        usd_cents=6000,
        price_id_live="price_1TNHgBGdPozm4cl0DzqAnsj5",
        price_id_sandbox="price_1TNHfiKIaHHghEpJe8f7M74R",
    ),
    "files_10000": PackDef(
        kind="files",
        size=10000,
        usd_cents=20000,
        price_id_live="price_1TNHgBGdPozm4cl0LAVPzdGv",
        price_id_sandbox="price_1TNHfjKIaHHghEpJv0Xsxp7G",
    ),
}


def resolve_price_id(pack_key: str, *, sandbox: bool = False) -> str:
    """Return the Stripe price id for ``pack_key``.

    Env-var override wins over the hardcoded id so ops can rotate without
    a redeploy: ``LINTPDF_STRIPE_PRICE_CREDITS_500`` (or ``_SANDBOX``
    suffix when sandbox=True).
    """
    defn = METERED_PACKS.get(pack_key)
    if defn is None:
        raise KeyError(f"Unknown pack: {pack_key}")
    env_name = f"LINTPDF_STRIPE_PRICE_{defn.kind.upper()}_{defn.size}"
    if sandbox:
        env_name += "_SANDBOX"
    return os.environ.get(env_name) or (defn.price_id_sandbox if sandbox else defn.price_id_live)


def list_packs(kind: PackKind) -> list[PackDef]:
    return [p for p in METERED_PACKS.values() if p.kind == kind]


def pack_for_size(kind: PackKind, size: int) -> PackDef | None:
    for p in METERED_PACKS.values():
        if p.kind == kind and p.size == size:
            return p
    return None
