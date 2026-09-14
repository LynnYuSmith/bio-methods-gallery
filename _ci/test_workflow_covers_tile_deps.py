"""The CI workflow must install everything the tiles declare.

Each tile is a standalone project that declares its own dependencies, but the
workflow installs a hand-written union of them. Nothing linked the two: on
2026-08-29 the `dff-baseline` tile started importing pandas, the workflow was
not updated, and the check went red with one tile erroring during collection.

This test is that link. It fails by naming the missing package, before a tile
does it with a collection error.

Run: python -m pytest _ci/
"""
import re
from pathlib import Path

try:                                  # py3.11+
    import tomllib
except ModuleNotFoundError:           # py3.10 — the other half of the CI matrix
    tomllib = None

from tiledeps import ROOT, _declared_in, _normalise, _requirement_name, tomllib  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"

# Installed from the repo itself (`pip install -e ./gallery_style`), so a tile
# may depend on it without the workflow naming it on a pip install line.
IN_REPO = {"gallery-style"}


def _installed_by_workflow():
    """Every package the workflow pip-installs, including across line continuations.

    Reading the file line by line missed a `pip install a b \\` continued onto the next line:
    the continuation does not start with "pip install", so everything on it was invisible and
    the test passed while CI would have failed. Continuations are joined first, and the "\\"
    itself is dropped rather than read as a package name.
    """
    text = re.sub(r"\\\s*\n\s*", " ", WORKFLOW.read_text())
    names = set()
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("pip install"):
            continue
        for token in line.split()[2:]:
            if token in ("\\",) or token.startswith("-") or token.startswith("."):
                continue                                          # flags, local paths
            names.add(_requirement_name(token))
    return names - {"pip"}


from tiledeps import tiles as _tiles  # noqa: E402


def test_a_continued_pip_line_is_read_to_its_end():
    """The blind spot this reader had: a package after a backslash was simply not seen."""
    import tempfile
    global WORKFLOW
    keep = WORKFLOW
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as fh:
            fh.write("        run: |\n"
                     "          pip install numpy scipy \\\n"
                     "                      tifffile mss\n")
            WORKFLOW = Path(fh.name)
        got = _installed_by_workflow()
    finally:
        WORKFLOW = keep
    assert {"numpy", "scipy", "tifffile", "mss"} <= got, got
    assert "\\" not in got, "the continuation marker was read as a package"


def test_the_reader_finds_something():
    """Positive control: a check that can only pass is not a check."""
    assert _tiles(), "no tiles found — the paths in this test are wrong"
    declared = set().union(*(_declared_in(p) for p in _tiles()))
    assert "numpy" in declared, f"dependency reader returned {declared!r}"
    installed = _installed_by_workflow()
    assert "numpy" in installed, f"workflow reader returned {installed!r}"


def test_workflow_installs_every_declared_dependency():
    installed = _installed_by_workflow() | IN_REPO
    missing = {}
    for pyproject in _tiles():
        gap = _declared_in(pyproject) - installed
        if gap:
            missing[pyproject.parent.name] = sorted(gap)
    assert not missing, (
        "these tiles declare packages the CI workflow does not install:\n  "
        + "\n  ".join(f"{tile}: {', '.join(pkgs)}" for tile, pkgs in sorted(missing.items()))
        + f"\nadd them to the pip install line in {WORKFLOW.relative_to(ROOT)}"
    )


def test_workflow_installs_pytest():
    """Without it every tile fails identically and the cause is off-screen."""
    assert "pytest" in _installed_by_workflow()


def test_the_fallback_parser_agrees_with_tomllib():
    """The py3.10 half of the matrix reads pyprojects by hand; tomllib is the oracle.

    A fallback that reads a different set is a check that passes for the wrong
    reason on half the matrix.
    """
    import test_workflow_covers_tile_deps as self_mod  # noqa: PLW0406

    if self_mod.tomllib is None:
        return  # running on 3.10: no oracle available, the other tests still apply
    real = self_mod.tomllib
    try:
        with_oracle = {p.parent.name: _declared_in(p) for p in _tiles()}
        self_mod.tomllib = None
        by_hand = {p.parent.name: _declared_in(p) for p in _tiles()}
    finally:
        self_mod.tomllib = real

    differing = {k: (sorted(with_oracle[k]), sorted(by_hand[k]))
                 for k in with_oracle if with_oracle[k] != by_hand[k]}
    assert not differing, f"fallback parser disagrees with tomllib: {differing}"
    assert with_oracle["dff-baseline"], "positive control: the oracle read nothing"
