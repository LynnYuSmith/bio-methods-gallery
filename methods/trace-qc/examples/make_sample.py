"""Synthetic calcium traces for two QC gates that live on two DIFFERENT representations.

SNR is a check on the **ΔF/F** trace (baseline already removed), photobleaching is a check on
the **raw fluorescence** (before ΔF/F, where the slow decay still lives). They answer different
questions about different versions of the signal, so the tile provides both:

  ΔF/F traces (for SNR):
    * clean   — sparse transients, low noise        → good SNR
    * noisy   — the same transients, buried in noise → low SNR
  raw fluorescence traces (for photobleaching):
    * raw_stable   — flat resting F0 + transients        → no decay
    * raw_bleached — resting F0 riding a strong exp decay → photobleaching

(On a raw trace the two are NOT independent: a decay strong enough to fit with a high r²
dominates the signal and wrecks its SNR — which is exactly why SNR is computed on ΔF/F, after
the baseline that removes the decay.)
"""
import numpy as np

FS = 60.0


def _calcium(n, fps, onsets, amps, tau=0.6):
    """A trace of exponential-decay calcium transients (no noise)."""
    x = np.zeros(n)
    for o, a in zip(onsets, amps):
        k = np.arange(n - o)
        x[o:] += a * np.exp(-k / (tau * fps))
    return x


def make_traces(n=3600, fps=FS, seed=0):
    """Return a dict: ΔF/F traces (clean, noisy), raw traces (raw_stable, raw_bleached), fps."""
    rng = np.random.RandomState(seed)
    n_ev = 22
    onsets = np.sort(rng.choice(np.arange(50, n - 200), size=n_ev, replace=False))
    amps = rng.uniform(0.8, 1.6, n_ev)
    events = _calcium(n, fps, onsets, amps)

    # ΔF/F traces (baseline already removed → no slow decay), for the SNR check
    clean = events + rng.normal(0, 0.04, n)
    noisy = events + rng.normal(0, 0.55, n)                       # same signal, ~14x noise

    # raw fluorescence traces (before ΔF/F), for the photobleaching check
    t = np.arange(n) / fps
    F0 = 1000.0
    raw_events = 220.0 * events                                  # transients in raw counts
    raw_stable = F0 + raw_events + rng.normal(0, 12.0, n)         # flat baseline, no bleach
    raw_bleached = F0 * np.exp(-t / 45.0) + raw_events + rng.normal(0, 12.0, n)   # ~45 s decay

    return {"fps": fps, "clean": clean, "noisy": noisy,
            "raw_stable": raw_stable, "raw_bleached": raw_bleached}


if __name__ == "__main__":
    s = make_traces()
    print({k: np.asarray(v).shape for k, v in s.items() if k != "fps"})
