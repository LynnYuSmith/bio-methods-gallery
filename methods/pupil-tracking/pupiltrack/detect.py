"""Per-frame pupil detection (Sonja Nevelchuk's algorithm, used with permission).

Threshold the dark pixels (the pupil is the darkest large structure in the eye ROI),
label the connected dark regions, and report each region's centroid and equivalent
radius (``r = sqrt(area / pi)``). The threshold is chosen per frame (Otsu), so there
is no fixed brightness cutoff.

Re-implemented in NumPy/SciPy so this tile stands alone. The value the tile shows is
in ``track.py`` (the tracking tool); this detector is the per-frame building block it
runs.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

try:  # scikit-image is the intended path; fall back to a midpoint threshold if absent
    from skimage.filters import threshold_otsu
except Exception:  # pragma: no cover
    threshold_otsu = None


def _threshold(f: np.ndarray, thr: float | None) -> float:
    if thr is not None:
        return float(thr)
    if threshold_otsu is not None:
        try:
            return float(threshold_otsu(f))
        except Exception:  # near-uniform frame (e.g. a blink): Otsu is undefined
            pass
    return float(0.5 * (f.min() + f.max()))


def detect_candidates(frame, min_area: int = 20, top_k: int = 3, thr: float | None = None):
    """Return up to ``top_k`` dark-blob candidates, largest first.

    Each candidate is ``(cy, cx, radius, area)`` in pixels. Regions smaller than
    ``min_area`` pixels are dropped as noise.
    """
    f = np.asarray(frame, dtype=float)
    t = _threshold(f, thr)
    mask = f < t  # the pupil is dark
    if not mask.any():
        return []

    labels, n = ndimage.label(mask)
    if n == 0:
        return []

    areas = ndimage.sum(np.ones_like(labels, dtype=float), labels, index=np.arange(1, n + 1))
    order = np.argsort(areas)[::-1]  # largest first

    out = []
    for idx in order[:top_k]:
        area = float(areas[idx])
        if area < min_area:
            continue
        label = int(idx) + 1
        cy, cx = ndimage.center_of_mass(mask, labels, label)
        radius = float(np.sqrt(area / np.pi))
        out.append((float(cy), float(cx), radius, area))
    return out


def detect_pupil(frame, **kwargs):
    """Largest dark blob only: ``(cy, cx, radius)`` or ``None``.

    This is the naive per-frame reading — no memory of previous frames — and is what
    the tracking tool improves on.
    """
    cands = detect_candidates(frame, **kwargs)
    if not cands:
        return None
    cy, cx, radius, _area = cands[0]
    return cy, cx, radius
