"""A tile must declare every third-party package it imports.

The other half of the same check. ``test_workflow_covers_tile_deps`` looks from the workflow's
side: does CI install what the tiles declare? This looks from the tile's side: does a tile
declare what it actually imports? On 2026-08-29 `dff-baseline` began importing pandas while
declaring only numpy and scipy, and the failure surfaced as a bare ``1 error`` during collection
in CI. Either check would have named the package instead.

A tile is a standalone project, so someone who clones one directory and reads its
``pyproject.toml`` has to get a working environment out of it — including the figure scripts,
which is why the extras count as declarations too.

Two things this deliberately does NOT flag:

* a declaration with no import. Nothing breaks, and a tile may reasonably declare something its
  README tells the reader to use.
* anything under ``.venv``, an egg-info or ``__pycache__``. A tile that has been run locally
  carries a whole site-packages tree, and walking into it reports several hundred phantom
  "imports" — which is how this check first read as twelve broken tiles.

Run: python -m pytest _ci/
"""
import ast
import sys
from pathlib import Path

from tiledeps import ROOT, _declared_in, _normalise, tiles

# import name -> distribution name, where they differ
DIST = {
    "skimage": "scikit-image",
    "cv2": "opencv-python",
    "PIL": "pillow",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "gallery_style": "gallery-style",
}
SKIP_PARTS = {".venv", "__pycache__", "build", "dist", ".pytest_cache", ".git"}
ALWAYS_AVAILABLE = {"pytest"}          # the test runner itself


def _py_files(tile_dir: Path):
    for p in sorted(tile_dir.rglob("*.py")):
        parts = set(p.parts)
        if parts & SKIP_PARTS or any(x.endswith(".egg-info") for x in p.parts):
            continue
        yield p


def _local_names(tile_dir: Path):
    """Modules and packages the tile provides itself, which need no declaration."""
    names = {p.stem for p in _py_files(tile_dir)}
    for d in tile_dir.iterdir():
        if d.is_dir() and d.name not in SKIP_PARTS and not d.name.endswith(".egg-info"):
            names.add(d.name)
    return names


def _third_party_imports(tile_dir: Path):
    """{distribution name: {relative paths that import it}}"""
    local = _local_names(tile_dir)
    std = set(sys.stdlib_module_names)
    found = {}
    for f in _py_files(tile_dir):
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:            # a deliberately broken fixture, if one ever exists
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module.split(".")[0]]
            else:
                continue
            for m in mods:
                if m in std or m in local:
                    continue
                dist = _normalise(DIST.get(m, m))
                found.setdefault(dist, set()).add(str(f.relative_to(tile_dir)))
    return found


def test_every_tile_declares_what_it_imports():
    gaps = {}
    for pyproject in tiles():
        tile = pyproject.parent
        declared = _declared_in(pyproject)
        imported = _third_party_imports(tile)
        missing = {d: sorted(where) for d, where in imported.items()
                   if d not in declared and d not in ALWAYS_AVAILABLE}
        if missing:
            gaps[tile.name] = missing
    assert not gaps, "\n".join(
        f"{t}: {d} imported by {', '.join(w)} but not declared in pyproject.toml"
        for t, m in gaps.items() for d, w in m.items())


def test_the_scan_sees_the_real_files_and_not_a_local_venv():
    """A guard on the guard: the walk must find the tile's own code and nothing else.

    If ``SKIP_PARTS`` ever stops working, this check silently starts scanning a cloned
    site-packages tree and its result becomes noise instead of a test.
    """
    for pyproject in tiles():
        tile = pyproject.parent
        files = list(_py_files(tile))
        assert files, f"{tile.name}: no python files found at all"
        assert len(files) < 60, (f"{tile.name}: {len(files)} python files — the walk is reaching "
                                 f"outside the tile's own code")
        assert not any(".venv" in str(f) for f in files)
