"""Is a bouton's trace trustworthy after 2-D motion correction?

Two failure modes a 2-D pipeline (Suite2p corrects x, y but not z) can leave behind:

* **residual xy motion** — the ROI still slides across the sensor, so the trace mixes in
  neighbouring pixels. Detected by TRACKING the bouton's local patch over time with the real
  pipeline registration engine (``register_fov_xy``, synced): a trustworthy bouton's patch
  barely moves; a drifting one accumulates a sub-pixel displacement bin after bin.

* **z-drift** — the bouton moves OUT of the focal plane, so its brightness falls and the trace
  reads as going quiet even though the cell never changed its firing. Suite2p can't see it. It
  is distinguished from FOV-wide photobleaching by comparing the bouton's own resting-F decline
  to the median decline across the field: a bouton that dims *faster than the field* is
  z-drifting, not just bleaching (and its patch does NOT move, which separates it from xy
  drift). The z-drift detector is the tile's own contribution.
"""
from __future__ import annotations

import numpy as np

from ._synced import register_fov_xy


def _box(roi):
    cy, cx, h = roi
    return int(cy), int(cx), int(h)


def roi_trace(stack, roi):
    """Summed fluorescence in the (fixed) ROI box, per frame → raw F (T,)."""
    cy, cx, h = _box(roi)
    patch = stack[:, cy - h:cy + h + 1, cx - h:cx + h + 1]
    return patch.reshape(patch.shape[0], -1).sum(axis=1).astype(float)


def _bin_means(stack, roi, n_bins):
    """Mean ROI patch image in each of ``n_bins`` time bins → list of 2-D patches."""
    cy, cx, h = _box(roi)
    patch = stack[:, cy - h:cy + h + 1, cx - h:cx + h + 1].astype(float)
    edges = np.linspace(0, patch.shape[0], n_bins + 1).astype(int)
    return [patch[edges[i]:edges[i + 1]].mean(axis=0) for i in range(n_bins)]


def residual_xy(stack, roi, n_bins: int = 8):
    """Track the bouton's patch across time bins → (max_displacement_px, trajectory[n_bins]).

    Each bin's mean patch is registered to the FIRST bin's patch with the pipeline's
    ``register_fov_xy``; the displacement of bin i is √(dx²+dy²). The max over bins is the
    residual-motion score (px). A well-corrected, non-drifting bouton stays near 0."""
    patches = _bin_means(stack, roi, n_bins)
    ref = patches[0]
    traj = [0.0]
    for p in patches[1:]:
        dx, dy, _peak = register_fov_xy(ref, p)
        traj.append(float(np.hypot(dx, dy)))
    return float(np.max(traj)), np.asarray(traj)


def resting_f(stack, roi, n_bins: int = 8, percentile: float = 20.0):
    """Resting fluorescence (a low percentile of the raw F, i.e. between events) per time bin."""
    f = roi_trace(stack, roi)
    edges = np.linspace(0, len(f), n_bins + 1).astype(int)
    return np.array([np.percentile(f[edges[i]:edges[i + 1]], percentile) for i in range(n_bins)])


def _frac_decline(series):
    """Fractional drop from the first bin to the last (0 = no decline, 1 = vanished)."""
    a, b = float(series[0]), float(series[-1])
    return (a - b) / a if a > 1e-9 else np.nan


def assess(stack, rois, *, n_bins: int = 8, shift_thresh_px: float = 1.0,
           zdrift_excess_thresh: float = 0.2):
    """Assess every ROI's trustworthiness. Returns ``{name: result}``.

    ``result`` has: ``residual_shift_px``, ``shift_trajectory``, ``resting_f`` (per bin),
    ``frac_decline``, ``zdrift_excess`` (decline beyond the FOV median), and ``verdict`` ∈
    {trustworthy, residual-motion, z-drift}. The FOV-wide decline (photobleaching) is the median
    ``frac_decline`` across all ROIs, so z-drift = a bouton declining *more than the field* while
    its patch stays put."""
    shift, rest, decline = {}, {}, {}
    for name, roi in rois.items():
        shift[name], traj = residual_xy(stack, roi, n_bins)
        rest[name] = resting_f(stack, roi, n_bins)
        decline[name] = _frac_decline(rest[name])
        rest[name] = (rest[name], traj)                      # stash traj alongside
    global_decline = float(np.nanmedian([decline[n] for n in rois]))   # FOV photobleaching

    out = {}
    for name, roi in rois.items():
        restf, traj = rest[name]
        excess = decline[name] - global_decline
        if shift[name] >= shift_thresh_px:
            verdict = "residual-motion"                      # patch moved → xy drift (checked first)
        elif excess >= zdrift_excess_thresh:
            verdict = "z-drift"                              # dims faster than the field, patch still
        else:
            verdict = "trustworthy"
        out[name] = {
            "residual_shift_px": shift[name], "shift_trajectory": traj,
            "resting_f": restf, "frac_decline": decline[name],
            "zdrift_excess": excess, "fov_decline": global_decline, "verdict": verdict,
        }
    return out
