"""Tile-facing API — thin wrappers over the REAL pipeline per-trace QC functions.

The maths lives in ``_synced.py`` (copied verbatim from the lab pipeline by ``_sync/sync.py``
and de-identified): SNR with a MAD-based noise floor, and an exponential photobleaching fit.
These wrappers give the demo and tests a small named vocabulary and fold in the A–F grade. Do
not reimplement the maths here — fix it in the pipeline and re-run the sync.

Both metrics apply to ANY calcium trace, soma or bouton. (Neuropil-contamination correction is
a soma-imaging concern and is not used for boutons; spatial trustworthiness — z-drift, residual
xy motion — lives in the separate trace-trustworthiness tile.)
"""
from __future__ import annotations

import numpy as np

from ._synced import QualityGrade, calculate_snr_per_trace, fit_exponential_decay


def snr(trace, fs: float = 60.0) -> dict:
    """SNR metrics for one trace + an A–F grade. Noise is the trace's MAD (× 1.4826), robust to
    sparse events and to either baseline convention. Returns the pipeline dict plus ``grade``."""
    r = calculate_snr_per_trace(np.asarray(trace, float), fs=fs)
    r["grade"] = QualityGrade.from_score(r["quality_score"]).value
    return r


def photobleaching(trace, fs: float = 60.0) -> dict:
    """Fit F(t) = A·exp(−t/τ) + B and report the decay. ``decay_rate`` is % signal lost per
    minute; ``r_squared`` gates it — a low r² means there is no real exponential decay to worry
    about, only noise the fit latched onto."""
    return fit_exponential_decay(np.asarray(trace, float), fs=fs)
