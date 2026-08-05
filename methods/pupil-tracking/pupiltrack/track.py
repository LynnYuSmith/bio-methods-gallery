"""The tracking tool (Lynn Smith) — the contribution this tile shows.

A per-frame detector (``detect.py``) guesses the pupil independently in every frame.
On its own it drifts: a corneal glint or a dark eyelid corner makes it pick the wrong
blob, and a blink makes it drop out. This tool runs the detector across the whole video
and keeps only what is temporally consistent:

  * pick, among the frame's candidates, the one nearest the previous pupil centre
    (movement gate) with a similar radius (size gate);
  * interpolate short gaps (blinks, brief losses);
  * lightly smooth the resulting trace.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .detect import detect_candidates


def _interp_gaps(a: np.ndarray, max_gap: int) -> np.ndarray:
    """Linearly interpolate interior NaN runs no longer than ``max_gap`` frames."""
    a = a.copy()
    n = len(a)
    isnan = np.isnan(a)
    i = 0
    while i < n:
        if isnan[i]:
            j = i
            while j < n and isnan[j]:
                j += 1
            if 0 < i and j < n and (j - i) <= max_gap:  # interior, short enough
                a[i:j] = np.linspace(a[i - 1], a[j], j - i + 2)[1:-1]
            i = j
        else:
            i += 1
    return a


def _smooth_valid(a: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian-smooth over the valid samples, leaving any remaining NaNs in place."""
    out = a.copy()
    valid = ~np.isnan(out)
    if valid.sum() >= 3:
        idx = np.where(valid)[0]
        out[idx] = gaussian_filter1d(out[idx].astype(float), sigma=sigma)
    return out


def track_pupil(
    frames,
    max_move: float = 8.0,
    max_dr: float = 4.0,
    max_gap: int = 5,
    smooth_sigma: float = 1.0,
    top_k: int = 3,
    **detect_kwargs,
):
    """Track the pupil across ``frames``.

    Returns a dict with per-frame arrays ``cy``, ``cx``, ``radius`` and ``status``
    (``"detected"`` / ``"interpolated"`` / ``"lost"``).
    """
    n = len(frames)
    cy = np.full(n, np.nan)
    cx = np.full(n, np.nan)
    radius = np.full(n, np.nan)
    status = ["lost"] * n
    prev = None  # (cy, cx, radius) of the last accepted frame

    for i, frame in enumerate(frames):
        cands = detect_candidates(frame, top_k=top_k, **detect_kwargs)
        pick = None
        if prev is None:
            pick = cands[0][:3] if cands else None  # bootstrap: largest blob
        else:
            best, best_dist = None, np.inf
            for cyi, cxi, ri, _area in cands:
                dist = float(np.hypot(cyi - prev[0], cxi - prev[1]))
                if dist <= max_move and abs(ri - prev[2]) <= max_dr and dist < best_dist:
                    best, best_dist = (cyi, cxi, ri), dist
            pick = best

        if pick is not None:
            cy[i], cx[i], radius[i] = pick
            status[i] = "detected"
            prev = pick

    cy = _interp_gaps(cy, max_gap)
    cx = _interp_gaps(cx, max_gap)
    radius = _interp_gaps(radius, max_gap)
    for i in range(n):
        if status[i] == "lost" and not np.isnan(radius[i]):
            status[i] = "interpolated"
    if smooth_sigma > 0:
        radius = _smooth_valid(radius, smooth_sigma)

    return {"cy": cy, "cx": cx, "radius": radius, "status": np.array(status, dtype=object)}
