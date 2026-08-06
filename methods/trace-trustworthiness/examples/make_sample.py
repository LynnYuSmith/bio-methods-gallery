"""An ALREADY motion-corrected 2-photon movie — where correction left residuals per bouton.

Global motion correction (Suite2p) removes the average frame shift, but the tissue does not move
as one rigid block: when the animal runs or moves, different parts of the field move by different
amounts, so each bouton keeps its OWN residual shift. And a big enough bout can push a bouton out
of its ROI — or out of the focal plane (z) — so that, for those frames, the ROI is measuring
background, not the bouton, no matter how good the global correction was.

This synthetic is the corrected movie: boutons fire independently of a **running** signal; during
running bouts each bouton gets its own residual in-plane jitter (non-uniform across the field),
the whole FOV dims/defocuses a little (z), and ONE bouton is shoved clean out of its ROI during
the strongest bout (it disappears). Ground truth: the running trace, per-bouton residual motion,
and which bouton disappears when.
"""
import numpy as np
from scipy.ndimage import gaussian_filter

FS = 60.0


def _gauss(H, W, cy, cx, sigma, amp):
    y, x = np.ogrid[:H, :W]
    return amp * np.exp(-((y - cy) ** 2 + (x - cx) ** 2) / (2 * sigma ** 2))


def _running_signal(T, fps, seed):
    rng = np.random.RandomState(seed)
    run = np.zeros(T)
    bouts = []
    for _ in range(3):
        c = rng.randint(int(2 * fps), T - int(2 * fps))
        w = int(rng.uniform(0.9, 1.6) * fps)
        seg = np.exp(-((np.arange(T) - c) ** 2) / (2 * (w / 2.5) ** 2))
        amp = rng.uniform(0.7, 1.0)
        run += amp * seg
        bouts.append((c, amp))
    return np.clip(run, 0, 1), bouts


def make_movie(T=1200, H=64, W=64, fps=FS, seed=0):
    """Return (stack[T,H,W], rois{name:(cy,cx,half)}, fps, truth)."""
    rng = np.random.RandomState(seed)
    sigma = 1.6
    centres = {"b0": (16, 16), "b1": (16, 48), "b2": (46, 22), "b3": (44, 46)}
    half = 6

    fire = {}
    for name in centres:
        onsets = np.sort(rng.choice(np.arange(30, T - 60), size=10, replace=False))
        f = np.zeros(T)
        for o in onsets:
            f[o:] += rng.uniform(0.7, 1.3) * np.exp(-(np.arange(T - o)) / (0.6 * fps))
        fire[name] = f

    run, bouts = _running_signal(T, fps, seed)
    strongest = max(range(len(bouts)), key=lambda i: bouts[i][1])
    strong_c = bouts[strongest][0]

    # per-bouton residual in-plane motion (each a different fraction of run — non-uniform field)
    res_amp = {"b0": 1.2, "b1": 1.8, "b2": 1.0, "b3": 1.5}
    local = {}
    for name in centres:
        j = rng.normal(0, 1, (T, 2))
        j = np.stack([np.convolve(j[:, 0], np.ones(5) / 5, "same"),
                      np.convolve(j[:, 1], np.ones(5) / 5, "same")], axis=1)
        local[name] = (run[:, None] * res_amp[name]) * j

    # b3 is shoved clean out of its ROI (> half) during the strongest bout: it disappears
    gone = np.exp(-((np.arange(T) - strong_c) ** 2) / (2 * (0.5 * fps) ** 2))
    local["b3"] = local["b3"] + gone[:, None] * np.array([14.0, 14.0])

    zdefocus = run * 0.45                                   # global z-defocus during bouts
    base_amp, event_amp = 900.0, 500.0

    stack = np.empty((T, H, W), np.float32)
    for f in range(T):
        frame = np.zeros((H, W))
        for name, (cy, cx) in centres.items():
            amp = base_amp + event_amp * fire[name][f]
            dy, dx = local[name][f]
            frame += _gauss(H, W, cy + dy, cx + dx, sigma, amp)
        if zdefocus[f] > 1e-3:
            frame = gaussian_filter(frame * (1 - zdefocus[f]), sigma=2.0 * zdefocus[f])
        stack[f] = frame

    stack *= np.exp(-0.15 * np.arange(T) / T)[:, None, None]    # mild photobleaching
    stack += rng.normal(0, 12.0, stack.shape)

    rois = {name: (cy, cx, half) for name, (cy, cx) in centres.items()}
    truth = {"run": run, "local": local, "disappears": "b3", "disappear_frame": int(strong_c),
             "fps": fps}
    return stack.astype(np.float32), rois, fps, truth


if __name__ == "__main__":
    stack, rois, fps, truth = make_movie()
    print(f"stack {stack.shape}, rois {list(rois)}, {truth['disappears']} disappears "
          f"~frame {truth['disappear_frame']}")
