"""Rolling-quantile baselines for ΔF/F, and the choice that decides where zero sits.

The baseline F0(t) is a rolling quantile of the fluorescence. The quantile decides where
the baseline lands in the noise, and with it what ΔF/F looks like:

* a MEDIAN baseline (q=0.5), left **unclipped**, sits in the middle of the noise, so
  ΔF/F = (F − F0) / F0 is symmetric around zero (honest two-sided noise; small dips
  below baseline survive);
* a LOWER-ENVELOPE baseline (a low quantile, q≈0.1, clipped to a positive floor) sits in
  the lower tail of the noise, below the resting level, so ΔF/F floats above zero — a
  positive bias, with one-sided noise.

Keeping the median baseline unclipped is the contribution.

The estimators are independent COPIES of the real lab-pipeline functions (``rolling_baseline``,
``maximin_baseline``), synced verbatim into ``_synced.py`` by ``_sync/sync.py`` and wrapped
here for a small named API. Fix the maths in the pipeline, then re-run the sync.
"""
from .baseline import (
    dff,
    floor_baseline,
    lower_envelope_baseline,
    median_baseline,
    rolling_quantile_baseline,
)

__all__ = [
    "rolling_quantile_baseline",
    "median_baseline",
    "lower_envelope_baseline",
    "floor_baseline",
    "dff",
]
