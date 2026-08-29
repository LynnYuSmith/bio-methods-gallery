"""De-identification for synced pipeline code, plus a fail-loud guard.

Synced tile code is copied verbatim from the private lab pipeline, which carries
lab-internal references — personal names, recording IDs, absolute user paths — that must
never ship in the public-facing gallery. :func:`deidentify` rewrites the known ones;
:func:`assert_clean` then RE-SCANS and raises if ANY forbidden token survives, so a missed
pattern fails the sync loudly instead of leaking silently.

The recording-ID handling deliberately does NOT anchor on a trailing ``\\b``: the lab's most
common form is ``<mouse>_<yymmdd>`` (e.g. ``cm027_260728``), and ``\\b`` fails before an
underscore (a word char), so the old pattern let that whole form pass. The guard is also
genuinely BROADER than the substitutions — a generic "letters+digits" ID shape (minus a small
allowlist of legitimate technical tokens like ``sha256``) — so an UNKNOWN prefix trips it and
forces a new substitution rule, rather than leaking.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

# Known lab recording/mouse-ID prefixes → rewritten to a neutral phrase. Underscore-date
# suffix (``_yymmdd``) is swallowed too. No trailing \b (see module docstring); a non-alnum
# lookbehind stops it matching inside a longer identifier.
_ID_PREFIXES = r"(?:cm|cf|cb|abm|abf|abc)"
_ID_SUB = rf"(?<![A-Za-z0-9]){_ID_PREFIXES}\d{{3,}}(?:_\d{{4,8}})?"

# Forbidden tokens are NOT written in this file: it is public, and a de-identifier that publishes
# the very tokens it hides defeats itself. They live in ``_sync/private_names.txt`` — one entry per
# line, ``token`` or ``token = replacement``, ``#`` comments — which is gitignored. See
# ``private_names.example.txt``. ``sync.py`` refuses to run when that file is missing, so an absent
# list can never leak silently.
NAMES_FILE = Path(__file__).with_name("private_names.txt")
DEFAULT_REPLACEMENT = "the lab"


def load_private_names(path: Path | None = None) -> list[tuple[str, str]]:
    """Read the private token list as (token, replacement) pairs; empty if the file is absent."""
    p = path or NAMES_FILE
    if not p.exists():
        return []
    out: list[tuple[str, str]] = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        token, sep, repl = ln.partition("=")
        out.append((token.strip(), repl.strip() if sep else DEFAULT_REPLACEMENT))
    return out


def name_rules(tokens: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Build (substitutions, forbidden) rules for a list of (token, replacement) pairs.

    Per token, in order: drop a parenthetical that mentions it (a cross-reference to something
    private is noise in a public tile), then the possessive form, then the bare token.
    """
    subs: list[tuple[str, str]] = []
    for tok, repl in tokens:
        esc = re.escape(tok)
        subs.append((rf"\s*\([^)]*{esc}[^)]*\)", ""))
        subs.append((rf"(?i)\b{esc}['\u2019]s\b", f"{repl}'s"))
        subs.append((rf"(?i)\b{esc}", repl))
    forbidden = [(rf"(?i)\b{re.escape(tok)}", "forbidden token") for tok, _ in tokens]
    return subs, forbidden


_NAME_SUBS, _NAME_FORBIDDEN = name_rules(load_private_names())

# (pattern, replacement), applied in order, to the raw synced source text.
SUBSTITUTIONS: list[tuple[str, str]] = [
    (r"/Users/[^\s\"')]+", ""),                         # absolute user paths
    (_ID_SUB, "a recording"),                           # mouse / recording IDs (+ _yymmdd)
    *_NAME_SUBS,
]

# After substitution, NONE of these may remain (label is for the error message). The
# ID-shape guard below is separate so it can carry an allowlist.
FORBIDDEN: list[tuple[str, str]] = [
    (r"/Users/", "absolute user path"),
    *_NAME_FORBIDDEN,
]

# Genuinely broad "looks like a recording/mouse ID" guard: 2–4 letters + 3–5 digits, bounded
# by non-alnum on the left and a non-digit on the right. Catches UNKNOWN prefixes the
# substitutions don't know about (cn045, abd012), while the 3–5-digit cap + trailing (?!\d)
# skips long DOI/ISBN digit runs (e.g. CBO9780511564345) that are not identifiers.
_IDLIKE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{2,4}\d{3,5}(?!\d)")
# Legitimate technical tokens that share the shape and are NOT identifying. Extend as needed.
_IDLIKE_ALLOW = {
    "sha256", "sha512", "sha384", "sha224", "iso8601", "rfc3339", "rfc2822",
}


def deidentify(text: str) -> str:
    """Rewrite known lab-internal references to neutral phrasing."""
    for pat, repl in SUBSTITUTIONS:
        text = re.sub(pat, repl, text)
    # tidy artefacts left by path removal: "(, " → "(", and collapse INLINE runs of spaces
    # only (lookbehind on a non-space char) so leading code indentation is preserved.
    text = re.sub(r"\(\s*,\s*", "(", text)
    # tidy the phrasing the token substitutions leave behind ("the <name> lab" -> "the lab")
    text = re.sub(r"(?i)\bthe lab lab\b", "the lab", text)
    text = re.sub(r"(?i)\bthe the\b", "the", text)
    text = re.sub(r"(?<=\S)[ \t]{2,}", " ", text)
    return text


def assert_clean(text: str, where: str = "") -> None:
    """Raise if any forbidden token (name, path, or ID-like shape) survived de-identification."""
    hits: list[str] = []

    def _record(start: int, end: int, label: str) -> None:
        ctx = text[max(0, start - 30):end + 30].replace("\n", " ")
        hits.append(f"  {label}: …{ctx}…")

    for pat, label in FORBIDDEN:
        for m in re.finditer(pat, text):
            _record(m.start(), m.end(), label)

    for m in _IDLIKE.finditer(text):
        if m.group(0).lower() in _IDLIKE_ALLOW:
            continue
        _record(m.start(), m.end(), f"ID-like token {m.group(0)!r} (unknown prefix?)")

    if hits:
        raise SystemExit(
            f"[sync] de-identification INCOMPLETE in {where}:\n"
            + "\n".join(hits)
            + "\n  → add a rule to _sync/deident.SUBSTITUTIONS (or _IDLIKE_ALLOW if it is a "
              "legitimate technical token, not an identifier)."
        )
