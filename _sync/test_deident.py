"""Tests for the de-identification guard. Run: python _sync/test_deident.py (or pytest)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deident import (  # noqa: E402
    assert_clean, deidentify, load_private_names, name_rules,
)


def _raises(text):
    try:
        assert_clean(text, "test")
        return False
    except SystemExit:
        return True


def test_underscore_dated_id_is_substituted_and_clean():
    # the common form <mouse>_<yymmdd> — the old \b-anchored rule let this pass.
    # IDs here are invented (this repo is public): same shape, no real recording.
    out = deidentify("session cm999_990101_axon_fixtest ran")
    assert "cm999" not in out and "990101" not in out, out
    assert_clean(out, "test")            # must not raise


def test_bare_and_spaced_ids_substituted():
    assert "cf999" not in deidentify("recorded cf999 today")
    assert "abm999" not in deidentify("mouse abm999")


def test_fresh_unknown_prefix_trips_the_guard():
    # cn045 / abd012 are NOT in the substitution list → the broad ID-shape guard must catch them
    assert _raises("cn045"), "unknown prefix cn045 should trip assert_clean"
    assert _raises("the abd012 mouse"), "unknown prefix abd012 should trip assert_clean"


def test_legit_technical_tokens_are_allowed():
    for tok in ("sha256", "iso8601", "rfc3339"):
        assert_clean(f"uses {tok} here", "test")     # must not raise


def test_doi_isbn_not_flagged():
    # long DOI/ISBN digit runs are not identifiers — the 3-5 digit cap + (?!\d) must skip them
    assert_clean("Fisher (1993), DOI:10.1017/CBO9780511564345 (§4.4)", "test")
    assert_clean("Mazurek 2014, DOI:10.3389/fncir.2014.00092", "test")


def test_paths_still_caught():
    assert _raises("/Users/someone/x")


def test_private_name_list_drives_the_name_rules():
    """Names live in a gitignored file, not in this public source — test the mechanism."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "private_names.txt"
        f.write_text("# a comment\nBloggs\n\nJane\nSECRET.md = the docs\n", encoding="utf-8")
        names = load_private_names(f)
        assert names == [("Bloggs", "the lab"), ("Jane", "the lab"),
                         ("SECRET.md", "the docs")], names

        subs, forbidden = name_rules(names)
        text = "Bloggs's method, reviewed by Jane"
        for pat, repl in subs:
            text = re.sub(pat, repl, text)
        assert "Bloggs" not in text and "Jane" not in text, text
        assert any(re.search(pat, "per Bloggs 2026") for pat, _ in forbidden)


def test_missing_name_file_yields_no_rules():
    assert load_private_names(Path("/nonexistent/private_names.txt")) == []


def test_parenthetical_cross_reference_is_dropped():
    """A "(see <private doc>)" aside is noise in a public tile — the whole aside goes."""
    subs, _ = name_rules([("SECRET.md", "the docs")])
    text = '    # the sign matters (see SECRET.md "Shift Convention")'
    for pat, repl in subs:
        text = re.sub(pat, repl, text)
    assert text == "    # the sign matters", repr(text)


def test_configured_tokens_trip_the_guard():
    _, forbidden = name_rules([("Bloggs", "the lab"), ("SECRET.md", "the docs")])
    assert all(any(re.search(pat, s) for pat, _ in forbidden)
               for s in ("per Bloggs 2026", "see SECRET.md"))


def test_code_indentation_preserved():
    src = "def f():\n    x = 1\n    return x\n"
    assert deidentify(src) == src            # no leading-space collapse


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            passed += 1
            print(f"  ✓ {name}")
    print(f"\n{passed} passed")
