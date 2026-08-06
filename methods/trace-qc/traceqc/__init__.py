"""Per-trace calcium QC: is the signal real, and is it un-bleached?

Two trace-intrinsic quality checks a single SNR cutoff can't both make:

* ``snr`` — signal-to-noise with a **MAD-based** noise floor (robust to sparse calcium
  events and to either baseline convention), plus an A–F grade. Separates a real trace from
  one that is mostly noise.
* ``photobleaching`` — fits F(t) = A·exp(−t/τ) + B and reports the % lost per minute, with an
  r² gate so a noisy trace isn't mistaken for a decaying one. A trace can have fine SNR yet be
  slowly bleaching — a different failure that SNR alone never sees.

Both apply to any calcium trace, soma or bouton. The estimators are independent COPIES of the
real lab-pipeline functions (``calculate_snr_per_trace``, ``fit_exponential_decay``), synced
verbatim into ``_synced.py`` by ``_sync/sync.py`` and wrapped here. Fix the maths in the
pipeline, then re-run the sync.
"""
from .qc import photobleaching, snr

__all__ = ["snr", "photobleaching"]
