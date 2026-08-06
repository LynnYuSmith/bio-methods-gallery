"""Tests for the de-identification guard. Run: python _sync/test_deident.py (or pytest)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deident import assert_clean, deidentify  # noqa: E402


def _raises(text):
    try:
        assert_clean(text, "test")
        return False
    except SystemExit:
        return True


def test_underscore_dated_id_is_substituted_and_clean():
    # the lab's most common form <mouse>_<yymmdd> — the old \b-anchored rule let this pass
    out = deidentify("session cm027_260728_axon_fixtest ran")
    assert "cm027" not in out and "260728" not in out, out
    assert_clean(out, "test")            # must not raise


def test_bare_and_spaced_ids_substituted():
    assert "cf016" not in deidentify("recorded cf016 today")
    assert "abm010" not in deidentify("mouse abm010")


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


def test_paths_and_names_still_caught():
    assert _raises("/Users/someone/x")
    assert _raises("per Polinka 2026")
    assert _raises("Sonja's detector")


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
