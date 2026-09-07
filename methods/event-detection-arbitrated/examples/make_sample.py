"""A synthetic recording that contains the trap this method exists for.

Two populations, both photon-noise limited, both passed through the same denoiser:

* **boutons** — a bright resting level (F0 ~ 180 counts) and real calcium transients at
  known times;
* **background** — a dim resting level (F0 ~ 10 counts) and NO events at all. Real
  recordings are full of these: regions that got an ROI but sit on tissue background.

Dividing by a small F0 is what makes the background's ΔF/F violent: shot noise is
sqrt(F0) counts, so the relative noise goes as 1/sqrt(F0) — about 4x worse at 10 counts
than at 180. Nothing about the background is special apart from being dim.

The denoiser is the second half of the trap. ``denoise_ar1`` is the shape every
deconvolution takes: rectify what rises above an AR(1) prediction, then re-convolve the
result with the indicator kernel. Run it on real transients and it recovers them; run it on
violent noise and it returns *smooth, plausible, positive* bumps. A detector that reads its
noise scale off that denoised trace cannot tell the two apart — which is the whole point of
the comparison the tile draws.
"""
from __future__ import annotations

import numpy as np

FPS = 30.0
TAU_S = 0.4          # indicator decay, seconds
RISE_S = 0.05        # indicator rise, seconds


def calcium_kernel(fps: float = FPS, tau_s: float = TAU_S, rise_s: float = RISE_S):
    """A single-exponential transient with a short rise, normalised to unit peak."""
    n = int(round(6 * tau_s * fps))
    t = np.arange(n) / fps
    k = (1.0 - np.exp(-t / rise_s)) * np.exp(-t / tau_s)
    return k / k.max()


def denoise_ar1(y, fps: float = FPS, tau_s: float = TAU_S, lam_k: float = 1.5):
    """Rectify what exceeds an AR(1) prediction beyond a sparsity penalty, then re-convolve.

    The shape every deconvolution takes, in three lines. The penalty ``lam_k`` (in units of
    the trace's own MAD noise) is what makes it SPARSE — without it, every positive residual
    survives and re-convolution inflates the noise instead of removing it, which is the
    opposite of what a solver does. With it, most of the noise goes to zero and the
    occasional large excursion comes back as a smooth, positive, event-shaped bump.

    Deliberately not a good solver: the tile's point must not depend on one.
    """
    y = np.asarray(y, float)
    g = float(np.exp(-1.0 / (tau_s * fps)))
    resid = y[1:] - g * y[:-1]
    lam = lam_k * 1.4826 * np.median(np.abs(resid - np.median(resid)))
    s = np.maximum(0.0, resid - lam)
    s = np.concatenate([[0.0], s])
    return np.convolve(s, calcium_kernel(fps, tau_s), mode="full")[: y.size]


def shared_background(T: int, fps: float, rng, motion_hz: float = 0.05):
    """The part of a recording that is not the cell: slow neuropil drift plus motion hits.

    White photon noise alone makes a dim ROI merely noisy. Real background is also
    CORRELATED — a slow neuropil tide and the occasional sharp motion excursion — and that is
    what makes a background trace cross its own median + k*sigma bar as often as a real
    bouton does. Returned in fluorescence-fraction units, so dividing by a small F0 amplifies
    it exactly as the recording does.
    """
    from numpy.fft import irfft, rfftfreq
    f = rfftfreq(T, d=1.0 / fps)
    amp = np.zeros_like(f)
    amp[1:] = 1.0 / f[1:]                       # 1/f tide
    phase = rng.uniform(0, 2 * np.pi, size=f.size)
    tide = irfft(amp * np.exp(1j * phase), n=T)
    tide = tide / (np.std(tide) + 1e-12)
    hits = np.zeros(T)
    k = rng.poisson(motion_hz * T / fps)
    kern = calcium_kernel(fps, tau_s=0.15)
    for fr in rng.integers(0, max(T - len(kern), 1), size=k):
        # POSITIVE only, and that asymmetry is the point: neuropil pulled into an ROI and
        # motion carrying brighter tissue across it both ADD fluorescence. A noise scale read
        # off the negative tail — the standard robust choice, since events live on the
        # positive side — therefore under-estimates what the positive side can do, and a
        # median + k*sigma bar on the measured trace sits too low to survive it.
        hits[fr:fr + len(kern)] += abs(rng.normal(0.0, 1.0)) * kern
    return np.abs(tide), hits


def rolling_median(y, win: int):
    """Centred rolling median, edges held — the slow-drift baseline a ΔF/F pipeline removes."""
    y = np.asarray(y, float)
    if win < 3 or win >= y.size:
        return np.full_like(y, float(np.median(y)))
    half = win // 2
    pad = np.concatenate([np.full(half, y[0]), y, np.full(half, y[-1])])
    idx = np.arange(y.size)[:, None] + np.arange(win)[None, :]
    return np.median(pad[idx], axis=1)


def make_sample(n_boutons: int = 40, n_background: int = 40, seconds: float = 120.0,
                fps: float = FPS, rate_hz: float = 0.25, f0_bouton: float = 180.0,
                f0_background: float = 10.0, neuropil_counts: float = 1.6,
                motion_counts: float = 2.2, seed: int = 0):
    """One synthetic recording. Returns a dict of (T, N) arrays plus the ground truth.

    Keys: ``dff`` (measured ΔF/F), ``reconstruct`` (the same traces denoised),
    ``intensities`` (raw counts), ``is_bouton`` (N,), ``true_events`` (list of frame
    arrays, empty for background), ``fps``.
    """
    rng = np.random.default_rng(seed)
    T = int(round(seconds * fps))
    n = n_boutons + n_background
    kern = calcium_kernel(fps)

    dff = np.zeros((T, n)); rec = np.zeros((T, n)); ints = np.zeros((T, n))
    is_bouton = np.zeros(n, bool); is_bouton[:n_boutons] = True
    truth: list[np.ndarray] = []

    tide, hits = shared_background(T, fps, rng)
    for j in range(n):
        f0 = f0_bouton if is_bouton[j] else f0_background
        clean = np.zeros(T)
        frames = np.array([], int)
        if is_bouton[j]:
            k = rng.poisson(rate_hz * seconds)
            frames = np.sort(rng.integers(0, T - len(kern), size=k)) if k else frames
            amp = rng.uniform(0.5, 1.5, size=len(frames))
            for fr, a in zip(frames, amp):
                clean[fr:fr + len(kern)] += a * kern
        truth.append(frames)
        # neuropil and motion arrive in COUNTS, so dividing by a small F0 amplifies them —
        # the same trace content is a ripple on a bright bouton and a storm on a dim ROI
        contamination = (neuropil_counts * tide + motion_counts * hits) / f0
        counts = rng.poisson(np.maximum(f0 * (1.0 + clean), 1e-9))
        ints[:, j] = counts
        raw = (counts - f0) / f0 + contamination
        # the same rolling baseline every ΔF/F pipeline applies. It takes the slow tide out
        # and leaves the sharp positive excursions in — which is why the measured trace ends
        # up with a modest sigma AND a fat positive tail, the worst combination for a
        # median + k*sigma bar read off that same trace.
        dff[:, j] = raw - rolling_median(raw, int(round(20.0 * fps)))
        rec[:, j] = denoise_ar1(dff[:, j], fps)

    return dict(dff=dff, reconstruct=rec, intensities=ints, is_bouton=is_bouton,
                true_events=truth, fps=fps, seconds=seconds)
