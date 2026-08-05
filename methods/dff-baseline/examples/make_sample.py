"""A synthetic fluorescence trace: a gently bleaching, slowly wandering resting level,
sparse positive calcium transients, and Gaussian noise.

The true ΔF/F is known. In the quiet stretches (no event) it is just noise — symmetric
around zero. That is what a median baseline should recover, and what a lower-envelope
baseline biases away from.
"""
import numpy as np


def make_trace(n: int = 3000, fps: float = 30.0, seed: int = 0):
    """Return a dict with ``f`` (fluorescence), ``fps``, ``f0_true`` (resting level),
    ``dff_true`` (true ΔF/F incl. noise), and ``quiet`` (bool mask of event-free frames)."""
    rng = np.random.RandomState(seed)
    t = np.arange(n) / fps

    # Resting fluorescence: gentle bleaching + a slow wander, always well above zero.
    f0_true = 1000.0 * np.exp(-t / 300.0) + 60.0 * np.sin(2 * np.pi * t / 40.0) + 500.0

    # Sparse positive calcium transients (exp decay, tau ~ 0.6 s), amplitudes vary.
    # Real boutons fire sparsely: keep the trace mostly quiet (~90% of frames), so the
    # rolling median genuinely sits in the noise rather than being pulled up by events.
    dff_events = np.zeros(n)
    onsets = rng.choice(np.arange(50, n - 100), size=8, replace=False)
    tau = 0.6
    for o in onsets:
        amp = rng.uniform(0.2, 1.5)
        dff_events[o:] += amp * np.exp(-np.arange(n - o) / (tau * fps))

    noise = rng.normal(0.0, 0.03, n)                 # ΔF/F-scale, symmetric
    f = f0_true * (1.0 + dff_events + noise)          # so (f - f0_true)/f0_true = events + noise
    quiet = dff_events < 0.02                         # frames essentially free of events

    return {"f": f, "fps": fps, "f0_true": f0_true, "dff_true": dff_events + noise, "quiet": quiet}


if __name__ == "__main__":
    s = make_trace()
    print(f"n={len(s['f'])}, fps={s['fps']}, quiet frames={int(s['quiet'].sum())}, "
          f"F range {s['f'].min():.0f}-{s['f'].max():.0f}")
