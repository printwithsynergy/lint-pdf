"""PDF Type-4 PostScript function evaluator (Ghostscript + fast-path).

PDF Type-4 functions (per ISO 32000-2 §7.10.5) are a deterministic subset
of PostScript. This module evaluates them via two layers:

1. **Fast-path** — recognize trivially-constant programs (e.g. ``{ pop 0 }``,
   ``{ pop pop 0 0 0 0 }``) via regex; return constants without subprocess.
2. **Ghostscript subprocess** — for non-trivial programs, shell out to
   ``gs -dNODISPLAY -dSAFER -``. gs is a runtime dep of the engine (see
   ``packages/engine/Dockerfile`` + Phase 0.1 inventory §B.2).

Results are memoized with ``lru_cache``: the same program + inputs combo
across pages/files only invokes gs once.

API (unchanged):

    >>> evaluate("{ 0.0 }", inputs=[0.5])
    [0.0]
    >>> evaluate("{ dup mul }", inputs=[0.5])
    [0.25]

Returns ``None`` on:
    - Ghostscript not on PATH
    - Subprocess timeout (5 s)
    - Non-zero exit
    - Output not parseable as numbers

Callers treat ``None`` as "could not verify".
"""

from __future__ import annotations

import re
import shutil
import subprocess
from functools import lru_cache

_GS_BIN = "gs"
_TIMEOUT_S = 5.0

# Fast-path regex for trivially-constant Type-4 programs.
# Matches `{ pop 0 }`, `{ pop pop 0 0 0 0 }`, etc. — N pops followed by
# M numeric constants, surrounded by whitespace + optional braces.
_CONSTANT_FAST_RE = re.compile(
    r"^\s*\{?\s*"
    r"(?:pop\s+)*"
    r"((?:[+-]?\d*\.?\d+\s*)+)"
    r"\}?\s*$"
)


def _gs_available() -> bool:
    """True iff ``gs`` is on PATH."""
    return shutil.which(_GS_BIN) is not None


def _fast_path_constants(program: str) -> tuple[float, ...] | None:
    """If ``program`` is trivially `{ pop ... pop CONST CONST ... }`, return
    the constant tuple; else None.

    Covers the most common Type-4 case (constant-zero tint transforms) with
    zero subprocess overhead.
    """
    match = _CONSTANT_FAST_RE.match(program)
    if not match:
        return None
    nums_blob = match.group(1).strip()
    parts = nums_blob.split()
    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        return None


def evaluate(program: str, *, inputs: list[float]) -> list[float] | None:
    """Evaluate a Type-4 PS program by piping it to Ghostscript.

    The program string should include the surrounding ``{ ... }``. Inputs
    are pushed onto the stack in order before execution. Returns the post-
    exec stack contents as a list of floats, or ``None`` on failure.

    PostScript driver:

        mark <inputs...> <program> exec counttomark array astore ==

    ``counttomark`` returns the count from top of stack to the mark, and
    ``array astore`` collects them into a single array which is then
    printed as ``[ a b c ]`` via ``==``. We strip the brackets and split
    on whitespace.
    """
    # Fast-path: detect trivially-constant programs and skip gs entirely.
    fast = _fast_path_constants(program)
    if fast is not None:
        return list(fast)

    return _evaluate_via_gs(program, tuple(float(x) for x in inputs))


def _evaluate_via_gs(program: str, inputs: tuple[float, ...]) -> list[float] | None:
    """Real gs invocation, memoized via lru_cache."""
    return _evaluate_via_gs_cached(program, inputs)


@lru_cache(maxsize=512)
def _evaluate_via_gs_cached(program: str, inputs: tuple[float, ...]) -> list[float] | None:
    if not _gs_available():
        return None

    inputs_str = " ".join(repr(x) for x in inputs)
    ps_driver = f"mark {inputs_str} {program} exec counttomark array astore ==\n"

    try:
        result = subprocess.run(
            [
                _GS_BIN,
                "-q",
                "-dNODISPLAY",
                "-dBATCH",
                "-dNOPAUSE",
                "-dSAFER",
                "-",
            ],
            input=ps_driver,
            text=True,
            capture_output=True,
            timeout=_TIMEOUT_S,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    if result.returncode != 0:
        return None

    return _parse_ps_array(result.stdout)


def _parse_ps_array(text: str) -> list[float] | None:
    """Parse a Ghostscript ``[ a b c ]`` output line into floats.

    Handles both ``[a b c]`` and ``[ a b c ]``; tolerates leading/trailing
    whitespace; returns None if any token cannot be parsed as float.
    """
    line = text.strip()
    if not line:
        return None
    # Take the first non-empty line of stdout (ignore any later "GS>" prompts)
    line = line.splitlines()[0].strip()
    if not (line.startswith("[") and line.endswith("]")):
        return None
    inner = line[1:-1].strip()
    if not inner:
        return []
    parts = inner.split()
    try:
        return [float(p) for p in parts]
    except ValueError:
        return None


__all__ = ["evaluate"]
