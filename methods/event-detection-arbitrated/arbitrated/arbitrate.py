"""Arbitrate a detector on a NULL population instead of arguing about it.

A calcium-event detector has one number that decides everything: the height its peaks must
clear, in units of "the noise". Every variant of that choice looks defensible on a trace you
already believe. The way to separate them is to run each one on data that **cannot** contain
events — regions that got an ROI but sit on tissue background — and ask how often it fires
there, as a fraction of how often it fires on real signal.

    false positives (%) = rate on the null population / rate on the real population x 100

A phase-randomised surrogate is not a usable null here: it preserves the total power,
including the energy of the real transients, so its own noise estimate is inflated and the
same detector variant can score anywhere from a few per cent to more than half depending
only on whose sigma it is handed. Real background from the same recording has no such
freedom.

Three variants are compared, which is the whole argument of this tile:

``dff_direct``
    peaks on the MEASURED trace, bar at ``median + k * sigma(measured)``. The classic.
``recon_own_sigma``
    peaks on the DENOISED trace, bar from that same denoised trace. Tempting, because the
    denoised trace is where the events are easy to see — and wrong, because denoising
    shrank its noise.
``arbitrated``
    peaks on the DENOISED trace, bar at ``calm-window baseline + k * sigma(MEASURED)``. The
    scale comes from the trace that still carries the noise; the peaks come from the trace
    where an event has a shape. Both are ratios to the same F0, so sigma transfers with no
    rescaling.
"""
from __future__ import annotations

from typing import Callable, Dict

import numpy as np

from ._synced import (calm_window_baseline, detect_events_arbitrated, detect_events_dff,
                      noise_sigma_negative_tail)

__all__ = ["detect", "population_rate", "false_positive_rate", "arbitrate", "VARIANTS"]


def detect(variant: str, dff, reconstruct, fps: float, clip_k: float = 4.0,
           prominence_k: float = 0.78, min_distance_s: float = 0.12):
    """Peak frames from one detector variant, for one trace pair."""
    dff = np.asarray(dff, float)
    rec = np.asarray(reconstruct, float)
    if variant == "dff_direct":
        return detect_events_dff(dff, fs=fps, clip_k=clip_k, prominence_k=prominence_k,
                                 min_distance_s=min_distance_s)
    if variant == "recon_own_sigma":
        # the bar read off the denoised trace: pass the reconstruct as the measured trace
        return detect_events_arbitrated(rec, rec, fs=fps, clip_k=clip_k,
                                        prominence_k=prominence_k,
                                        min_distance_s=min_distance_s, guard=False)
    if variant == "arbitrated":
        return detect_events_arbitrated(rec, dff, fs=fps, clip_k=clip_k,
                                        prominence_k=prominence_k,
                                        min_distance_s=min_distance_s, guard=False)
    raise ValueError(f"unknown variant {variant!r}; choose from {VARIANTS}")


VARIANTS = ("dff_direct", "recon_own_sigma", "arbitrated")


def population_rate(variant: str, dff, reconstruct, mask, fps: float, **kw) -> float:
    """Events per second per trace, over the traces ``mask`` selects."""
    dff = np.asarray(dff, float)
    rec = np.asarray(reconstruct, float)
    mask = np.asarray(mask, bool)
    if not mask.any():
        return float("nan")
    seconds = dff.shape[0] / float(fps)
    n = 0
    for j in np.flatnonzero(mask):
        n += len(detect(variant, dff[:, j], rec[:, j], fps, **kw))
    return n / (seconds * mask.sum())


def false_positive_rate(variant: str, dff, reconstruct, is_real, fps: float, **kw) -> Dict:
    """One variant's rates on both populations, and the ratio between them."""
    is_real = np.asarray(is_real, bool)
    real = population_rate(variant, dff, reconstruct, is_real, fps, **kw)
    null = population_rate(variant, dff, reconstruct, ~is_real, fps, **kw)
    return dict(variant=variant, real_per_s=real, null_per_s=null,
                false_positive_pct=100.0 * null / real if real > 0 else float("nan"))


def arbitrate(sample: Dict, clip_k: float = 4.0, **kw):
    """Every variant against the null population of one sample. Small is better."""
    return [false_positive_rate(v, sample["dff"], sample["reconstruct"],
                                sample["is_bouton"], sample["fps"], clip_k=clip_k, **kw)
            for v in VARIANTS]


def noise_ratio(sample: Dict) -> Dict:
    """Why the arbitrated variant works: how much noise the denoiser hides, per population.

    The measured-over-denoised sigma ratio is small for real signal and large for
    background — so the measured trace's sigma is exactly the quantity that can still see
    what denoising smoothed away.
    """
    out = {}
    for name, m in (("bouton", sample["is_bouton"]), ("background", ~sample["is_bouton"])):
        r = [noise_sigma_negative_tail(sample["dff"][:, j])
             / max(noise_sigma_negative_tail(sample["reconstruct"][:, j]), 1e-12)
             for j in np.flatnonzero(m)]
        out[name] = float(np.median(r))
    return out


def baseline_vs_median(sample: Dict) -> Dict:
    """The other half of the choice: the calm-window baseline against the plain median."""
    fps = sample["fps"]
    out = {}
    for name, m in (("bouton", sample["is_bouton"]), ("background", ~sample["is_bouton"])):
        b = [calm_window_baseline(sample["reconstruct"][:, j], fps)
             for j in np.flatnonzero(m)]
        med = [float(np.median(sample["reconstruct"][:, j])) for j in np.flatnonzero(m)]
        out[name] = dict(calm_window=float(np.median(b)), median=float(np.median(med)))
    return out
