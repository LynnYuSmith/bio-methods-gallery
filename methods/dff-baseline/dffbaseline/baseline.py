"""Tile-facing baseline API — thin wrappers over the REAL pipeline functions.

The actual maths lives in ``_synced.py``, copied verbatim from the lab pipeline
(``rolling_baseline``, ``maximin_baseline``) by ``_sync/sync.py`` and de-identified. These
wrappers only give the demo and tests a small, named vocabulary for what the tile is about:
where the baseline sits (median vs lower-envelope quantile) and the suite2p FLOOR.

Do not reimplement the maths here — fix it in the pipeline and re-run the sync.
"""
from __future__ import annotations

import numpy as np

from ._synced import maximin_baseline, rolling_baseline


def rolling_quantile_baseline(y, fps: float = 30.0, win_s: float = 20.0, q: float = 0.5):
    """Rolling ``q``-quantile baseline — the real ``rolling_baseline`` (light Gaussian
    post-smooth, and the auto clamp-below-signal that fires only for a lower-envelope
    quantile, q < 0.3). ``q=0.5`` is the median, ``q=0.1`` a lower envelope."""
    return rolling_baseline(np.asarray(y, dtype=float), fps=fps, win_s=win_s, q=q)


def median_baseline(y, fps: float = 30.0, win_s: float = 20.0):
    """Zero-centred mode: a rolling median (q=0.5), left UNCLIPPED (the clamp auto-turns off
    at q ≥ 0.3) — the reason ΔF/F comes out symmetric around zero."""
    return rolling_baseline(np.asarray(y, dtype=float), fps=fps, win_s=win_s, q=0.5)


def lower_envelope_baseline(y, fps: float = 30.0, win_s: float = 20.0, q: float = 0.1, floor=None):
    """Classic mode: a low rolling quantile, clamped below the signal (auto for q < 0.3), so
    ΔF/F floats above zero. Optional positive ``floor`` guards a near-zero baseline."""
    b = rolling_baseline(np.asarray(y, dtype=float), fps=fps, win_s=win_s, q=q)
    return b if floor is None else np.clip(b, floor, None)


def floor_baseline(y, fps: float = 60.0, win_s: float = 60.0, sig_frames: float = 10.0):
    """suite2p maximin FLOOR (real ``maximin_baseline``): a running min → max envelope that
    hugs the bottom of the trace, so median-height events survive the subtraction (unlike a
    q ≈ 0.5 quantile, which sits mid-signal and subtracts them away)."""
    return maximin_baseline(np.asarray(y, dtype=float), fps=fps, win_s=win_s, sig_frames=sig_frames)


def dff(y, f0):
    """ΔF/F = (y − F0) / F0."""
    y = np.asarray(y, dtype=float)
    f0 = np.asarray(f0, dtype=float)
    return (y - f0) / f0
