"""SpotNameSimilarityAnalyzer — flags suspiciously similar spot color
names (typos, case inconsistencies).

The 2026-04-28 Opus audit flagged this on the Amalgam_Catalyst fixture:
*"Spot color name typo: '/Dark Biege' should be 'Dark Beige'.
Misspelled separation names will not merge with correctly-named
instances downstream and create an extra unintended plate."*

Plus on the same fixture: *"Inconsistent capitalization in spot color
names ('BUFF' all-caps vs. 'Lt Beige', 'Med Beige', 'Faint Beige' title
case) suggests they were created in different sessions/files and may
not consolidate cleanly."*

Both shapes produce duplicate plates at output: the RIP treats names
as case-sensitive, character-exact strings, so ``Biege`` and ``Beige``
become two separate plates even though the operator clearly meant one.

Check IDs:
    LPDF_SPOT_NAME_TYPO — Two spot color names differ by ≤ 2
        character edits (likely typo). Severity: WARNING.
    LPDF_SPOT_NAME_CASE — Two spot names match when lowercased but
        differ in case style. Severity: WARNING.

Calibration:
* Pantone names are excluded from the typo check — variants like
  ``PANTONE 225 C`` and ``PANTONE 226 C`` are intentionally
  different and shouldn't be flagged.
* Process channel names (Cyan, Magenta, Yellow, Black) are
  excluded — they're handled by ``LPDF_SPOT_DUPE_PROCESS``.
* Names shorter than 4 characters skip the typo check (too short
  for edit-distance to be meaningful).
* Pair-wise dedupe: each ``(a, b)`` pair emits one finding.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Process channel names — handled by LPDF_SPOT_DUPE_PROCESS, skip here.
_PROCESS_NAMES: frozenset[str] = frozenset(
    {
        "cyan",
        "magenta",
        "yellow",
        "black",
        "white",
        "red",
        "green",
        "blue",
        "gray",
        "grey",
    }
)

# Pantone-style identifiers. Names matching this pattern are
# intentionally enumerated by Pantone book; treat each as distinct.
_PANTONE_PATTERN = re.compile(
    r"^pantone\s+",
    re.IGNORECASE,
)
_PMS_PATTERN = re.compile(
    r"^pms\s+",
    re.IGNORECASE,
)
# Dieline / ProcessingStep names — already handled by dieline analyzers.
_DIELINE_NAMES: frozenset[str] = frozenset(
    {
        "dieline",
        "die_line",
        "cutcontour",
        "cut_contour",
        "cutting",
        "crease",
        "perforating",
        "kiss_cut",
        "kisscut",
        "fold_line",
        "perf_line",
        "white_base",
        "varnish",
    }
)

# Edit distance threshold below which two names are flagged as
# likely typos. 1 = single character substitution / insertion /
# deletion; 2 = up to two such edits. Tune to taste — anything
# higher starts firing on legitimately distinct color variants.
_MAX_TYPO_DISTANCE = 2

# Minimum length for the typo check. Below this, edit distance
# measurements collapse onto noise (every 3-letter pair has
# distance ≤ 2 from many others).
_MIN_TYPO_NAME_LEN = 4


def _normalise(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.strip().strip("/").replace("-", "_").replace(" ", "_")


def _is_excluded(name: str) -> bool:
    """True when ``name`` is a process / Pantone / dieline name we
    deliberately skip."""
    norm = (_normalise(name) or "").lower()
    if norm in _PROCESS_NAMES or norm in _DIELINE_NAMES:
        return True
    raw = name.strip().strip("/")
    return bool(_PANTONE_PATTERN.match(raw) or _PMS_PATTERN.match(raw))


def _levenshtein(a: str, b: str, max_dist: int = _MAX_TYPO_DISTANCE) -> int:
    """Compute the Levenshtein edit distance between ``a`` and ``b``,
    bounded above by ``max_dist + 1`` so callers can short-circuit on
    "too far" pairs without paying the full quadratic cost.
    """
    if abs(len(a) - len(b)) > max_dist:
        return max_dist + 1
    if a == b:
        return 0
    # Standard DP.
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        row_min = i
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(
                curr[j - 1] + 1,
                prev[j] + 1,
                prev[j - 1] + cost,
            )
            row_min = min(row_min, curr[j])
        if row_min > max_dist:
            return max_dist + 1
        prev = curr
    return prev[-1]


def _collect_spot_names(document: SemanticDocument) -> list[str]:
    """Return every spot/devicen colorant name across the document
    (preserving original casing). Deduplicated by exact original
    string."""
    seen_exact: set[str] = set()
    out: list[str] = []
    for page in document.pages:
        for cs in (page.color_spaces or {}).values():
            cs_type = getattr(cs, "cs_type", None)
            if cs_type not in ("Separation", "DeviceN", "NChannel"):
                continue
            for colorant in getattr(cs, "colorant_names", None) or ():
                if not colorant or colorant in ("All", "None"):
                    continue
                if colorant in seen_exact:
                    continue
                seen_exact.add(colorant)
                out.append(colorant)
    return out


class SpotNameSimilarityAnalyzer(BaseAnalyzer):
    """Flag suspiciously similar spot color names (typos + case
    inconsistencies) that produce duplicate plates at output."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        all_names = _collect_spot_names(document)

        # LPDF_SPOT_NAME_WHITESPACE — applies to ALL spot names
        # (including Pantone) because stray whitespace / trailing
        # punctuation in the colorant name is the defect itself.
        # Cherry-Twist had ``PANTONE 3582 C.  `` with a trailing
        # period + two spaces — produces a separately named plate
        # from the clean ``PANTONE 3582 C`` if any other artwork
        # ever uses the clean form.
        whitespace_seen: set[str] = set()
        for n in all_names:
            cleaned = n.strip().rstrip(".,;:").rstrip()
            if cleaned == n or n in whitespace_seen:
                continue
            whitespace_seen.add(n)
            findings.append(
                Finding(
                    inspection_id="LPDF_SPOT_NAME_WHITESPACE",
                    severity=Severity.WARNING,
                    message=(
                        f"Spot color name {n!r} has stray whitespace or "
                        f"trailing punctuation. Cleaned form would be "
                        f"{cleaned!r}. The RIP treats spot names as "
                        "character-exact strings, so this produces a "
                        "separately named plate from any artwork that "
                        "uses the clean name and breaks DFE "
                        "spot-name matching/aliasing."
                    ),
                    details={
                        "raw_name": n,
                        "cleaned_name": cleaned,
                    },
                    category="color",
                    object_type="document",
                )
            )

        names = [n for n in all_names if not _is_excluded(n)]
        if len(names) < 2:
            return findings

        # Case-inconsistency check. Build a map from lower-case form
        # to the original casings observed; emit when ≥ 2 distinct
        # casings share a lower-case key.
        case_groups: dict[str, list[str]] = {}
        for n in names:
            key = n.strip().strip("/").lower()
            case_groups.setdefault(key, [])
            if n not in case_groups[key]:
                case_groups[key].append(n)
        case_emitted: set[str] = set()
        for key, variants in case_groups.items():
            if len(variants) < 2:
                continue
            if key in case_emitted:
                continue
            case_emitted.add(key)
            findings.append(
                Finding(
                    inspection_id="LPDF_SPOT_NAME_CASE",
                    severity=Severity.WARNING,
                    message=(
                        f"Spot color names with inconsistent casing: "
                        f"{', '.join(repr(v) for v in variants)} "
                        "all map to the same colorant when lowercased "
                        "but the RIP treats them as separate plates. "
                        "Pick one canonical casing and re-route all "
                        "artwork to it before plating."
                    ),
                    details={"variants": variants, "canonical_lower": key},
                    category="color",
                    object_type="document",
                )
            )

        # Typo / near-duplicate check. Compare every unordered pair
        # of names not already flagged as case-only mismatches.
        emitted_pairs: set[frozenset[str]] = set()
        for i, a in enumerate(names):
            if len(a) < _MIN_TYPO_NAME_LEN:
                continue
            a_norm = (_normalise(a) or "").lower()
            for b in names[i + 1 :]:
                if len(b) < _MIN_TYPO_NAME_LEN:
                    continue
                b_norm = (_normalise(b) or "").lower()
                if a_norm == b_norm:
                    # Already covered by case check.
                    continue
                dist = _levenshtein(a_norm, b_norm)
                if dist == 0 or dist > _MAX_TYPO_DISTANCE:
                    continue
                pair = frozenset({a, b})
                if pair in emitted_pairs:
                    continue
                emitted_pairs.add(pair)
                findings.append(
                    Finding(
                        inspection_id="LPDF_SPOT_NAME_TYPO",
                        severity=Severity.WARNING,
                        message=(
                            f"Spot color names {a!r} and {b!r} differ by "
                            f"only {dist} character edit{'s' if dist != 1 else ''} — "
                            "likely typo. Misspelled separation names will "
                            "not merge with correctly-named instances at "
                            "the RIP and create an extra unintended plate."
                        ),
                        details={
                            "name_a": a,
                            "name_b": b,
                            "edit_distance": dist,
                        },
                        category="color",
                        object_type="document",
                    )
                )

        # PR-N (audit miss closure): token-level comparison. Names
        # like '/Dark Biege' vs '/Faint Beige' / '/Lt Beige' /
        # '/Med Beige' share modifier-prefix vocabulary but their
        # full strings are too far apart for the whole-string
        # Levenshtein. Compare equivalently-positioned tokens (or
        # the last token, which most often carries the colour-family
        # name) instead.
        token_pairs_emitted: set[frozenset[str]] = set()
        for i, a in enumerate(names):
            a_tokens = [t for t in _tokenise(a) if len(t) >= _MIN_TYPO_NAME_LEN]
            if not a_tokens:
                continue
            for b in names[i + 1 :]:
                b_tokens = [t for t in _tokenise(b) if len(t) >= _MIN_TYPO_NAME_LEN]
                if not b_tokens:
                    continue
                # Compare every cross pair of tokens. If ANY pair
                # differs by 1-2 edits AND at least one matches an
                # existing token verbatim from the rest of the
                # inventory, treat the close pair as a typo.
                for ta in a_tokens:
                    for tb in b_tokens:
                        if ta == tb:
                            continue
                        d = _levenshtein(ta, tb)
                        if d == 0 or d > _MAX_TYPO_DISTANCE:
                            continue
                        # Confirm at least one of (ta, tb) appears
                        # verbatim somewhere else in the inventory —
                        # rules out one-off coincidental near-matches.
                        all_tokens: set[str] = set()
                        for n in names:
                            all_tokens.update(_tokenise(n))
                        if ta not in all_tokens or tb not in all_tokens:
                            continue
                        pair = frozenset({a, b})
                        if pair in emitted_pairs or pair in token_pairs_emitted:
                            continue
                        token_pairs_emitted.add(pair)
                        findings.append(
                            Finding(
                                inspection_id="LPDF_SPOT_NAME_TYPO",
                                severity=Severity.WARNING,
                                message=(
                                    f"Spot color names {a!r} and {b!r} share "
                                    f"a modifier-suffix structure where one "
                                    f"token ({ta!r}) differs from another "
                                    f"({tb!r}) by only {d} edit"
                                    f"{'s' if d != 1 else ''} — likely typo. "
                                    "RIP treats them as separate plates."
                                ),
                                details={
                                    "name_a": a,
                                    "name_b": b,
                                    "token_a": ta,
                                    "token_b": tb,
                                    "edit_distance": d,
                                },
                                category="color",
                                object_type="document",
                            )
                        )
        return findings


def _tokenise(name: str) -> list[str]:
    """Split a normalised spot-color name into lowercase tokens
    on whitespace / underscore / hyphen boundaries."""
    norm = (_normalise(name) or "").lower()
    return [t for t in norm.split("_") if t]
