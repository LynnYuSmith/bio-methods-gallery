"""Tuning significance: a trial-shuffle test on OSI, Benjamini-Hochberg FDR, a bootstrap
CI, and a Rayleigh test.

The honest population call uses the **shuffle test**: the OSI point estimate is positively
biased, but its bias is exactly what a shuffle reproduces — permute the per-trial responses
across orientation slots, recompute OSI, and the observed OSI is significant only if it
beats that biased null. Shuffle p-values are valid (uniform under the null), so
**Benjamini-Hochberg FDR** across the population genuinely controls the false-discovery
rate. (A Rayleigh test on the mean responses is provided too, but a Rayleigh test on
rectified baseline-subtracted responses has a non-uniform null, so it is not the basis of
the population call.)
"""
from __future__ import annotations

import numpy as np

from .selectivity import osi


def rayleigh_test(angles_deg, weights=None) -> tuple[float, float]:
    """Rayleigh test for non-uniformity of circular data → ``(z, p)``.

    The weights (the response across orientations) set the resultant-vector length ``r``,
    but the sample size for the z-statistic is the **number of sampled directions**, not
    Kish's effective n on the weights — Kish inverts the test's power for tuning (a sharply
    tuned cell would collapse to n_eff≈1 and never reach significance). Closed form from
    Fisher (1993), *Statistical Analysis of Circular Data*, §4.4.
    """
    angles_deg = np.asarray(angles_deg, dtype=float)
    n = len(angles_deg)
    if n < 2:
        return np.nan, np.nan
    ang = np.deg2rad(angles_deg)
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    w = np.maximum(w, 0.0)                      # circular weights are magnitudes (≥0)
    w_sum = w.sum()
    if not np.isfinite(w_sum) or w_sum <= 0:
        return np.nan, np.nan
    w = w / w_sum
    x = np.sum(w * np.cos(ang))
    y = np.sum(w * np.sin(ang))
    r = np.hypot(x, y)
    z = n * r ** 2
    p = np.exp(-z) * (
        1
        + (2 * z - z ** 2) / (4 * n)
        - (24 * z - 132 * z ** 2 + 76 * z ** 3 - 9 * z ** 4) / (288 * n ** 2)
    )
    return float(z), float(np.clip(p, 0, 1))


def shuffle_test_osi(trials, orientations, n_shuffle: int = 500, seed: int = 0) -> tuple[float, float]:
    """Shuffle test for OSI, z-scored against the shuffle null → ``(osi_obs, p)``.

    ``trials`` is ``(n_orientations, n_trials)``. The null permutes every per-trial response
    across all orientation×trial slots (destroying any orientation structure) and recomputes
    OSI. Rather than counting shuffles that beat the observed OSI (whose resolution floors at
    ``1/n_shuffle`` — too coarse once Benjamini-Hochberg multiplies by a whole population),
    the observed OSI is **z-scored against the shuffle mean and SD** and ``p`` is the upper
    Gaussian tail. This gives continuous p-values that can go far below ``1/n_shuffle`` for a
    clearly tuned cell, so the population FDR call can still reach significance. (This mirrors
    the pipeline's shuffle test, which reports both a z-score and a p-value.)
    """
    import math

    trials = np.asarray(trials, dtype=float)
    orientations = np.asarray(orientations, dtype=float)
    n_ori, n_tr = trials.shape
    obs = osi(np.nanmean(trials, axis=1), orientations)
    if not np.isfinite(obs):
        return obs, np.nan
    flat = trials.reshape(-1)
    rng = np.random.RandomState(seed)
    null = np.empty(n_shuffle)
    for i in range(n_shuffle):
        shuffled = rng.permutation(flat).reshape(n_ori, n_tr)
        null[i] = osi(np.nanmean(shuffled, axis=1), orientations)
    null = null[np.isfinite(null)]
    if null.size < 2:
        return float(obs), np.nan
    mu, sd = float(np.mean(null)), float(np.std(null))
    if sd <= 0:
        return float(obs), (0.0 if obs > mu else 1.0)
    z = (obs - mu) / sd
    p = 0.5 * math.erfc(z / math.sqrt(2.0))       # one-sided upper tail
    return float(obs), float(min(max(p, 1e-12), 1.0))


def benjamini_hochberg(pvals) -> np.ndarray:
    """Benjamini-Hochberg FDR-adjusted q-values for a family of p-values.

    ``q_i`` is the smallest FDR at which test ``i`` is still called significant; compare
    ``q < alpha``. NaN p-values pass through as NaN and do not count toward ``m``.
    """
    p = np.asarray(pvals, dtype=float)
    q = np.full(p.shape, np.nan)
    finite = np.where(np.isfinite(p))[0]
    if finite.size == 0:
        return q
    pv = p[finite]
    m = pv.size
    order = np.argsort(pv)
    ranked = pv[order]
    adj = ranked * m / (np.arange(1, m + 1))
    adj = np.minimum.accumulate(adj[::-1])[::-1]     # enforce monotonicity
    adj = np.clip(adj, 0, 1)
    out = np.empty(m)
    out[order] = adj
    q[finite] = out
    return q


def bootstrap_osi_ci(trials, orientations, n_boot: int = 1000, ci: float = 95.0, seed: int = 0):
    """Percentile bootstrap CI for OSI by resampling trials within each orientation.

    ``trials`` is ``(n_orientations, n_trials)``. Returns ``(osi_point, lo, hi)``.
    """
    trials = np.asarray(trials, dtype=float)
    orientations = np.asarray(orientations, dtype=float)
    point = osi(np.nanmean(trials, axis=1), orientations)
    rng = np.random.RandomState(seed)
    _n_ori, n_tr = trials.shape
    boot = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.randint(0, n_tr, size=n_tr)
        boot[b] = osi(np.nanmean(trials[:, idx], axis=1), orientations)
    lo, hi = np.nanpercentile(boot, [(100 - ci) / 2, 100 - (100 - ci) / 2])
    return float(point), float(lo), float(hi)


def classify_population(trials_by_bouton, orientations, osi_thr: float = 0.33,
                        alpha: float = 0.05, n_shuffle: int = 500, seed: int = 0):
    """Classify each bouton as tuned two ways.

    ``trials_by_bouton`` is ``(n_boutons, n_orientations, n_trials)`` of per-trial responses.

    * ``naive`` = ``osi > osi_thr`` on the mean responses (no significance).
    * ``honest`` = shuffle-test p-value, Benjamini-Hochberg-corrected across the population,
      with ``q < alpha``.

    Returns per-bouton arrays: ``osi``, ``pval`` (shuffle), ``qval`` (BH), ``naive``,
    ``honest``.
    """
    T = np.asarray(trials_by_bouton, dtype=float)
    orientations = np.asarray(orientations, dtype=float)
    osis = np.empty(T.shape[0])
    pvals = np.empty(T.shape[0])
    for i in range(T.shape[0]):
        osis[i], pvals[i] = shuffle_test_osi(T[i], orientations, n_shuffle=n_shuffle, seed=seed + i)
    qvals = benjamini_hochberg(pvals)
    naive = osis > osi_thr
    honest = qvals < alpha
    return {"osi": osis, "pval": pvals, "qval": qvals, "naive": naive, "honest": honest}
