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

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"

# Installed from the repo itself (`pip install -e ./gallery_style`), so a tile
# may depend on it without the workflow naming it on a pip install line.
IN_REPO = {"gallery-style"}


def _normalise(name):
    """PEP 503: fold case and collapse -_. runs, so gallery_style == gallery-style."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(spec):
    """'scikit-image>=0.20' -> 'scikit-image'."""
    return _normalise(re.split(r"[<>=!~;\[ ]", spec.strip(), 1)[0])


def _declared_in(pyproject):
    """Every dependency a tile declares — runtime and every optional extra."""
    text = pyproject.read_text()
    if tomllib is not None:
        project = tomllib.loads(text).get("project", {})
        specs = list(project.get("dependencies", []))
        for extra in project.get("optional-dependencies", {}).values():
            specs += list(extra)
        return {_requirement_name(s) for s in specs}
    # Fallback for py3.10, where tomllib does not exist. Section-aware on
    # purpose: a bare `key = [...]` scan also swallows the package lists under
    # [tool.setuptools.packages.find]. Verified against tomllib in
    # test_the_fallback_parser_agrees_with_tomllib.
    specs, table, buf = [], None, None
    for line in text.splitlines():
        stripped = line.strip()
        if buf is None and stripped.startswith("[") and stripped.endswith("]") and "=" not in stripped:
            table = stripped[1:-1].strip()
            continue
        if buf is None:
            if table == "project" and stripped.startswith("dependencies"):
                pass
            elif table == "project.optional-dependencies" and "=" in stripped:
                pass
            else:
                continue
            buf = stripped.split("=", 1)[1]
        else:
            buf += " " + stripped
        if "]" in buf:
            specs += re.findall(r'"([^"]+)"', buf[: buf.index("]") + 1])
            buf = None
    return {_requirement_name(s) for s in specs}


def _installed_by_workflow():
    names = set()
    for line in WORKFLOW.read_text().splitlines():
        line = line.strip()
        if not line.startswith("pip install"):
            continue
        for token in line.split()[2:]:
            if token.startswith("-") or token.startswith("."):   # flags, local paths
                continue
            names.add(_requirement_name(token))
    return names - {"pip"}


def _tiles():
    return sorted((ROOT / "methods").glob("*/pyproject.toml"))


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
