"""A synthetic recording: active boutons (fluctuate in time) plus a static bright shaft.

The point is the difference between bright and active. The boutons vary frame to frame (they fire);
the shaft is bright in every frame but never changes. A mean-image detector sees both; an
activity-based detector sees only the boutons.
"""
import numpy as np


def make_recording(n_frames=60, y=128, x=128, pixel_size_um=0.3, seed=0):
    """Return (stack, pixel_size_um, truth) with stack (frames, y, x)."""
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:y, 0:x]
    truth = []                                        # (row, col, is_bouton)

    def blob(cy, cx, sigma_px, amp):
        return (amp * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sigma_px ** 2))).astype("float32")

    boutons = []
    for _ in range(22):                               # active boutons, ~1.5 um
        cy, cx = rng.randint(10, y - 10), rng.randint(10, x - 10)
        boutons.append((cy, cx, rng.uniform(1.4, 2.2)))
        truth.append((cy, cx, True))

    # a static bright shaft: a thick elongated ridge, bright in EVERY frame, never fluctuating
    shaft = np.zeros((y, x), "float32")
    for t in np.linspace(0, 1, 60):
        cy, cx = int(20 + t * (y - 40)), int(30 + t * 20)
        shaft += blob(cy, cx, 5.0, 0.9)
    shaft = np.clip(shaft, 0, 1.5)
    for t in np.linspace(0.1, 0.9, 4):                # mark a few points on the shaft as artifacts
        truth.append((int(20 + t * (y - 40)), int(30 + t * 20), False))

    stack = np.empty((n_frames, y, x), "float32")
    for f in range(n_frames):
        frame = shaft.copy()                          # shaft is present, unchanged, every frame
        for (cy, cx, s) in boutons:                   # boutons fire independently over time
            frame += blob(cy, cx, s, rng.uniform(0.0, 1.2))
        frame += rng.normal(0, 0.03, (y, x)).astype("float32")
        stack[f] = frame
    return stack, pixel_size_um, truth


if __name__ == "__main__":
    st, ps, truth = make_recording()
    print(f"stack {st.shape}, {ps} um/px, "
          f"{sum(t[2] for t in truth)} active boutons + {sum(not t[2] for t in truth)} shaft points")
