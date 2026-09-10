"""Run the per-frame border measurement across a video with temporal consistency.

The per-frame detector in ``detect.py`` is deliberately memoryless and deliberately willing to
refuse. This layer supplies the memory and decides what to do with the refusals:

* **anchoring.** Each frame's centre search starts from the previous accepted centre and is
  restricted to a disc around it. This is what keeps the measurement on the pupil when a
  brighter structure — lid glare, a reflection at the edge of the window — appears elsewhere in
  the frame. A memoryless detector has no way to prefer the pupil, because nothing in a single
  frame says the pupil is the interesting bright thing.
* **re-acquisition.** After a run of refusals (a blink) the anchor is stale, so the search is
  released to the whole frame again rather than pinned to where the eye used to be.
* **short gaps are interpolated, long ones are not.** A three-frame blink between two solid
  measurements can be bridged honestly. A hundred-frame loss cannot, and a trace that pretends
  otherwise will be averaged by someone downstream.
* **a transient jump is refused.** A pupil dilates smoothly; a diameter that leaps and returns
  within a couple of frames is the fit moving, not the eye. The jump guard compares each frame
  with the local median and drops the outliers instead of smoothing them away, so what remains
  is measurement rather than a filtered blend of measurement and error.

Nothing here smooths the surviving samples. Smoothing hides exactly the disagreement that tells
you the measurement went wrong, and a caller who wants a smooth trace can smooth it knowingly.
"""
from __future__ import annotations

import numpy as np

from .detect import detect_border


def _interp_gaps(a: np.ndarray, max_gap: int) -> np.ndarray:
    """Linearly bridge interior NaN runs no longer than ``max_gap`` frames."""
    out = a.copy()
    n = len(out)
    isnan = np.isnan(out)
    i = 0
    while i < n:
        if isnan[i]:
            j = i
            while j < n and isnan[j]:
                j += 1
            if 0 < i and j < n and (j - i) <= max_gap:
                out[i:j] = np.linspace(out[i - 1], out[j], j - i + 2)[1:-1]
            i = j
        else:
            i += 1
    return out


def _refuse_jumps(radius: np.ndarray, win: int = 11, tol: float = 4.0):
    """NaN the frames whose radius is far from the local median. Returns (radius, n_refused)."""
    out = radius.copy()
    n = len(out)
    bad = np.zeros(n, bool)
    half = win // 2
    for i in range(n):
        if np.isnan(out[i]):
            continue
        lo, hi = max(0, i - half), min(n, i + half + 1)
        neigh = out[lo:hi]
        neigh = neigh[np.isfinite(neigh)]
        if len(neigh) >= 5 and abs(out[i] - np.median(neigh)) > tol:
            bad[i] = True
    out[bad] = np.nan
    return out, int(bad.sum())


def track_pupil(frames, search_px: float = 20.0, max_gap: int = 5,
                reacquire_after: int = 3, jump_tol: float = 4.0, **detect_kwargs):
    """Track the pupil border across ``frames`` (an ``(n, H, W)`` eye-ROI stack).

    Returns a dict of per-frame arrays: ``cy``, ``cx``, ``radius``, ``residual``, ``arc_deg``,
    ``contrast`` and ``status`` — ``"measured"``, ``"interpolated"`` or the detector's own
    refusal reason (``"no_contrast"``, ``"short_arc"``, ``"poor_fit"``, …).
    """
    n = len(frames)
    cy = np.full(n, np.nan)
    cx = np.full(n, np.nan)
    radius = np.full(n, np.nan)
    resid = np.full(n, np.nan)
    arc = np.full(n, np.nan)
    contrast = np.full(n, np.nan)
    status = np.array(["lost"] * n, dtype=object)

    anchor = None
    misses = 0
    for i in range(n):
        r = detect_border(frames[i], anchor=anchor, search_px=search_px, **detect_kwargs)
        resid[i], arc[i], contrast[i] = r["residual"], r["arc_deg"], r["contrast"]
        if r["status"] == "ok":
            cy[i], cx[i], radius[i] = r["cy"], r["cx"], r["radius"]
            status[i] = "measured"
            anchor = (r["cy"], r["cx"])
            misses = 0
        else:
            status[i] = r["status"]
            misses += 1
            if misses >= reacquire_after:      # the anchor is stale; search the frame again
                anchor = None

    radius, n_jump = _refuse_jumps(radius, tol=jump_tol)
    for i in range(n):
        if status[i] == "measured" and np.isnan(radius[i]):
            status[i] = "transient_jump"

    filled = _interp_gaps(radius, max_gap)
    for i in range(n):
        if np.isnan(radius[i]) and not np.isnan(filled[i]):
            status[i] = "interpolated"
    radius = filled
    cy = _interp_gaps(cy, max_gap)
    cx = _interp_gaps(cx, max_gap)

    return {"cy": cy, "cx": cx, "radius": radius, "residual": resid, "arc_deg": arc,
            "contrast": contrast, "status": status, "n_transient_refused": n_jump}
