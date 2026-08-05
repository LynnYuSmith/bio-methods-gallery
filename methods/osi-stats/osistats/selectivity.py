"""The OSI point estimate (reproduced from the pipeline's ``analysis/selectivity``).

OSI = (R_pref − R_orth) / (R_pref + R_orth), with directions folded into orientation
space [0°, 180°) and negative responses rectified to 0 (on zero-centred ΔF/F the
orthogonal response can go negative; without rectification the denominator can vanish
and the most selective cells drop out). Reference: Mazurek, Kager & Van Hooser (2014),
Front. Neural Circuits, DOI:10.3389/fncir.2014.00092.
"""
from __future__ import annotations

import numpy as np


def osi(responses, orientations, clip_negative: bool = True) -> float:
    """Orientation Selectivity Index in [0, 1] (``nan`` if undefined)."""
    responses = np.asarray(responses, dtype=float)
    orientations = np.asarray(orientations, dtype=float)
    if len(responses) < 2 or np.all(np.isnan(responses)):
        return np.nan
    valid = ~np.isnan(responses)
    if not np.any(valid):
        return np.nan
    if clip_negative:
        responses = np.where(valid, np.maximum(responses, 0.0), responses)

    # Fold directions into orientation space: R_ori(θ) = R(θ) + R(θ+180°).
    ori_mod = orientations % 180
    ori_sum = {}
    for o in np.unique(ori_mod):
        paired = (ori_mod == o) & valid
        if np.any(paired):
            ori_sum[o] = np.nansum(responses[paired])
    if len(ori_sum) < 2:
        return np.nan

    oris = np.array(list(ori_sum.keys()))
    resps = np.array(list(ori_sum.values()))

    pref_idx = int(np.argmax(resps))
    r_pref = resps[pref_idx]
    orth_ori = (oris[pref_idx] + 90) % 180
    d = np.abs(oris - orth_ori)
    d = np.minimum(d, 180 - d)
    r_orth = resps[int(np.argmin(d))]

    denom = r_pref + r_orth
    if denom <= 0:
        return np.nan
    return float(np.clip((r_pref - r_orth) / denom, 0, 1))
