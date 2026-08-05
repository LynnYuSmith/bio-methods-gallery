"""Rolling-quantile baseline estimators for ΔF/F."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import percentile_filter


def rolling_quantile_baseline(y, fps: float = 30.0, win_s: float = 20.0, q: float = 0.5):
    """Rolling ``q``-quantile of ``y`` over a centred window of ``win_s`` seconds.

    ``q`` in [0, 1]; ``q=0.5`` is the median, ``q=0.1`` a lower envelope. The window is
    ``win_s * fps`` frames (at least 3), edges handled by nearest-value padding.
    """
    y = np.asarray(y, dtype=float)
    size = max(3, int(round(win_s * fps)))
    pct = float(np.clip(q, 0.0, 1.0) * 100.0)
    return percentile_filter(y, percentile=pct, size=size, mode="nearest")


def dff(y, f0):
    """ΔF/F = (y − F0) / F0."""
    return (np.asarray(y, dtype=float) - np.asarray(f0, dtype=float)) / np.asarray(f0, dtype=float)


def median_baseline(y, fps: float = 30.0, win_s: float = 20.0):
    """The zero-centred mode: a rolling median (q=0.5), left **unclipped** so it can sit
    wherever the resting level is — the reason ΔF/F comes out symmetric around zero."""
    return rolling_quantile_baseline(y, fps=fps, win_s=win_s, q=0.5)


def lower_envelope_baseline(y, fps: float = 30.0, win_s: float = 20.0, q: float = 0.1, floor: float = 1.0):
    """The classic mode: a low rolling quantile, **clipped** to a positive floor.

    Sits in the lower tail of the noise (below the resting level), which pushes ΔF/F above
    zero. The clip only bites when the raw baseline approaches zero.
    """
    b = rolling_quantile_baseline(y, fps=fps, win_s=win_s, q=q)
    return np.clip(b, floor, None)
