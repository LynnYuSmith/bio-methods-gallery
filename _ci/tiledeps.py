"""What a tile declares — shared by the checks that compare it with something else.

Two questions are asked of these numbers, from opposite sides: does the workflow install what
the tiles declare (``test_workflow_covers_tile_deps``), and do the tiles declare what they
import (``test_tiles_declare_what_they_import``). Both need the same parsing, and the py3.10
fallback below is the fiddly part, so it lives in one place with one test proving it agrees with
tomllib.
"""
import re
from pathlib import Path

try:                                  # py3.11+
    import tomllib
except ModuleNotFoundError:           # py3.10 — the other half of the CI matrix
    tomllib = None

ROOT = Path(__file__).resolve().parent.parent


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



def tiles():
    return sorted((ROOT / "methods").glob("*/pyproject.toml"))
