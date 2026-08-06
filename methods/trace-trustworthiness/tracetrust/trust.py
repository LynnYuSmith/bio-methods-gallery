"""Per-ROI residual-motion trustworthiness on an already motion-corrected movie.

Global motion correction removes the average frame shift, but the tissue is not rigid: when the
animal runs or moves, each bouton keeps its OWN residual shift (the field moves non-uniformly),
and a big enough bout can push a bouton out of its ROI or out of the focal plane (z) so the ROI
measures background, not the bouton. So the question is asked PER ROI, on that bouton's own pixels.

For each ROI, each frame's local patch is registered to a still template of the same patch with
the pipeline's ``register_fov_xy`` — which returns both things we need at once:

* **displacement √(dx²+dy²)** — how far this bouton's pixels shifted after global correction
  (residual in-plane motion at this location);
* **peak correlation = presence** — how well the patch still matches the bouton's footprint. It
  falls when the bouton leaves the patch, laterally OR by z-defocus — i.e. when the bouton has
  effectively **disappeared from the field of view** and the trace is measuring background.

A frame is untrustworthy for a bouton if its residual shift is large or its presence is low; and
if a running trace is given, those flags line up with movement.
"""
from __future__ import annotations

import numpy as np

from ._synced import register_fov_xy


def _patch(stack, roi, pad):
    cy, cx, h = int(roi[0]), int(roi[1]), int(roi[2])
    r = h + int(pad)
    return stack[:, cy - r:cy + r + 1, cx - r:cx + r + 1].astype(float)


def roi_motion(stack, roi, *, pad: int = 3, stride: int = 2):
    """Per-frame (displacement_px, presence) for one ROI's local patch, via ``register_fov_xy``.

    ``presence`` is the post-alignment correlation peak ∈ [0, 1]: ~1 when the bouton is there and
    matchable, low when it has left the patch (lateral motion) or defocused (z). ``stride`` skips
    frames and interpolates (registration is the cost)."""
    patch = _patch(stack, roi, pad)
    ref = np.median(patch, axis=0)
    T = patch.shape[0]
    idx = np.arange(0, T, stride)
    disp = np.empty(len(idx))
    pres = np.empty(len(idx))
    for i, f in enumerate(idx):
        dx, dy, peak = register_fov_xy(ref, patch[f])
        disp[i] = float(np.hypot(dx, dy))
        pres[i] = float(peak)
    g = np.arange(T)
    return np.interp(g, idx, disp), np.interp(g, idx, pres)


def _z(a):
    a = np.asarray(a, float)
    s = a.std()
    return (a - a.mean()) / s if s > 1e-9 else a * 0.0


def assess(stack, rois, fps, *, run=None, disp_thr_px: float = 1.5, presence_thr: float = 0.6,
           gone_thr: float = 0.4, pad: int = 3, stride: int = 2):
    """Assess every ROI's residual-motion trustworthiness → ``{name: result}``.

    ``result``: ``displacement`` (px, per frame), ``presence`` (per frame), ``motion_flag``
    (residual shift ≥ ``disp_thr_px`` OR presence ≤ ``presence_thr``), ``gone_flag`` (presence ≤
    ``gone_thr`` — the bouton left the FOV / defocused, so the ROI reads background),
    ``max_shift_px``, ``frac_untrustworthy``, ``frac_gone``, ``disappeared`` (bool). With a
    ``run`` trace, ``run_corr`` (Pearson of the per-frame motion score with running)."""
    out = {}
    for name, roi in rois.items():
        disp, pres = roi_motion(stack, roi, pad=pad, stride=stride)
        motion_flag = (disp >= disp_thr_px) | (pres <= presence_thr)
        gone_flag = pres <= gone_thr
        res = {
            "displacement": disp, "presence": pres,
            "motion_flag": motion_flag, "gone_flag": gone_flag,
            "max_shift_px": float(np.max(disp)),
            "frac_untrustworthy": float(motion_flag.mean()),
            "frac_gone": float(gone_flag.mean()),
            "disappeared": bool(gone_flag.any()),
        }
        if run is not None:
            run = np.asarray(run, float)
            score = _z(disp) - _z(pres)                 # more shift / less presence = more motion
            res["run_corr"] = float(np.corrcoef(score, run)[0, 1]) if np.std(run) > 0 else np.nan
        out[name] = res
    return out
