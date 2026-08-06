"""A synthetic 2-photon movie of three boutons, each with a known trustworthiness problem.

After 2-D motion correction a bouton's trace is only trustworthy if the ROI keeps measuring the
SAME bouton for the whole recording. Two ways that fails, plus a clean control — all under a
mild global photobleaching so the z-drift detector has to separate a bouton's own dimming from
the FOV-wide bleaching:

  * stable  — fixed position, steady brightness            → trustworthy
  * xy_drift — the bouton slowly slides in x, y            → residual motion after MC
  * z_drift  — the bouton dims as it leaves the focal plane → falsely "silent" (a z-artifact,
               not a real drop in activity)

Suite2p corrects x, y but not z, so z-drift is invisible to it: the bouton's brightness falls
and the trace reads as going quiet even though the cell never changed its firing.
"""
import numpy as np

FS = 60.0


def _gauss(H, W, cy, cx, sigma, amp):
    y, x = np.ogrid[:H, :W]
    return amp * np.exp(-((y - cy) ** 2 + (x - cx) ** 2) / (2 * sigma ** 2))


def make_movie(T=1200, H=64, W=64, fps=FS, seed=0):
    """Return (stack[T,H,W], rois{name:(cy,cx,half)}, fps, truth{name:mode})."""
    rng = np.random.RandomState(seed)
    t = np.arange(T)
    sigma = 1.6

    # each bouton fires the same sparse event train (so a dimming is clearly NOT less firing)
    onsets = np.sort(rng.choice(np.arange(30, T - 60), size=14, replace=False))
    fire = np.zeros(T)
    for o in onsets:
        fire[o:] += rng.uniform(0.6, 1.2) * np.exp(-(np.arange(T - o)) / (0.6 * fps))

    boutons = {
        "stable":   dict(cy=16, cx=16, mode="stable"),
        "xy_drift": dict(cy=16, cx=48, mode="xy_drift"),
        "z_drift":  dict(cy=46, cx=32, mode="z_drift"),
    }
    base_amp = 900.0
    event_amp = 500.0

    stack = np.zeros((T, H, W), np.float32)
    for f in range(T):
        frame = np.zeros((H, W))
        for b in boutons.values():
            cy, cx = float(b["cy"]), float(b["cx"])
            amp = base_amp + event_amp * fire[f]
            if b["mode"] == "xy_drift":
                cy += 4.0 * f / T                    # slides ~4 px in y and x over the movie
                cx += 4.0 * f / T
            elif b["mode"] == "z_drift":
                amp *= np.exp(-3.0 * f / T)          # dims to ~5% as it defocuses out of plane
            frame += _gauss(H, W, cy, cx, sigma, amp)
        stack[f] = frame

    stack *= np.exp(-0.22 * t / T)[:, None, None]     # mild global photobleaching (~20% by end)
    stack += rng.normal(0, 12.0, stack.shape)

    rois = {name: (b["cy"], b["cx"], 6) for name, b in boutons.items()}   # FIXED ROI boxes
    truth = {name: b["mode"] for name, b in boutons.items()}
    return stack.astype(np.float32), rois, fps, truth


if __name__ == "__main__":
    stack, rois, fps, truth = make_movie()
    print(f"stack {stack.shape}, rois {list(rois)}, truth {truth}")
