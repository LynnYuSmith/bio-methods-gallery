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

# Known lab recording/mouse-ID prefixes → rewritten to a neutral phrase. Underscore-date
# suffix (``_yymmdd``) is swallowed too. No trailing \b (see module docstring); a non-alnum
# lookbehind stops it matching inside a longer identifier.
_ID_PREFIXES = r"(?:cm|cf|cb|abm|abf|abc)"
_ID_SUB = rf"(?<![A-Za-z0-9]){_ID_PREFIXES}\d{{3,}}(?:_\d{{4,8}})?"

# (pattern, replacement), applied in order, to the raw synced source text.
SUBSTITUTIONS: list[tuple[str, str]] = [
    (r"/Users/[^\s\"')]+", ""),                         # absolute user paths
    (_ID_SUB, "a recording"),                           # mouse / recording IDs (+ _yymmdd)
    (r"(?i)\bPolinka['’]s\b", "the lab's"),
    (r"(?i)\bPolinka\b", "the lab"),
    (r"(?i)\bPolina\b", "the lab"),
    (r"(?i)\bSonja\b", "the lab"),
    (r"(?i)\bNevelchuk\b", "the lab"),
    (r"(?i)\bGaraschuk\b", "the lab"),
    (r"(?i)\bKoval\b", "the lab"),
]

# After substitution, NONE of these may remain (label is for the error message). The
# ID-shape guard below is separate so it can carry an allowlist.
FORBIDDEN: list[tuple[str, str]] = [
    (r"/Users/", "absolute user path"),
    (r"(?i)\bpolinka\b", "personal name (Polinka)"),
    (r"(?i)\bpolina\b", "personal name (Polina)"),
    (r"(?i)\bsonja\b", "personal name (Sonja)"),
    (r"(?i)\bnevelchuk\b", "personal name"),
    (r"(?i)\bgaraschuk\b", "personal name"),
    (r"(?i)\bkoval\b", "personal name"),
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
