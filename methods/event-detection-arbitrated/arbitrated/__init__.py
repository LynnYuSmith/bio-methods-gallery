"""Detect calcium events on the denoised trace, with the noise scale from the measured one.

Deconvolution makes events easy to see — and that is the trap. A dim, background-level ROI
has a violently noisy ΔF/F (shot noise divided by a tiny F0), and its denoised trace is that
same noise smoothed into perfectly plausible, positive, event-shaped bumps. A detector that
takes its height bar from the denoised trace has no way to know: denoising shrank the very
quantity the bar is measured in.

So take the two halves from the two traces:

    threshold = calm_window_baseline(denoised) + clip_k * sigma_negative_tail(measured)

peaks on the denoised trace, scale from the measured one. Both are ratios to the same F0, so
sigma transfers directly. And the reference is the trace's own calm baseline, not its median,
because on an active trace the median sits inside the activity.

The claim is settled on a NULL population rather than by argument — regions that got an ROI
but cannot host events — and reported as false positives relative to the real rate. See
``arbitrate``.

The estimators here are independent COPIES of the lab-pipeline functions, synced verbatim
into ``_synced.py`` and wrapped for a small named API. Fix the maths in the pipeline, then
re-run the sync.
"""
from ._synced import (bouton_unit_usable, calm_window_baseline, derive_prominence_k,
                      detect_events_arbitrated, detect_events_dff,
                      noise_sigma_negative_tail, recovered_f0)
from .arbitrate import (VARIANTS, arbitrate, baseline_vs_median, detect,
                        false_positive_rate, noise_ratio, population_rate)

__all__ = [
    "detect_events_arbitrated", "detect_events_dff", "calm_window_baseline",
    "noise_sigma_negative_tail", "derive_prominence_k", "bouton_unit_usable",
    "recovered_f0",
    "detect", "population_rate", "false_positive_rate", "arbitrate", "noise_ratio",
    "baseline_vs_median", "VARIANTS",
]
