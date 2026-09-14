#!/usr/bin/env python3
"""A synthetic 'screen': a viewer window showing an eye, dark between recordings.

No real data is shipped in this gallery. What is reproduced here is the SHAPE of the problem —
a region that is dark while the rig is idle and lit while it records, with a retro-reflective
pupil that changes size — because that shape is what the gate and the region handling exist to
deal with.
"""
from __future__ import annotations

import numpy as np

W, H = 320, 200
PUPIL_C = (150, 95)


def frame(t: int, lit: bool, rng: np.random.RandomState) -> np.ndarray:
    """One grab of the 'screen' at step ``t``."""
    img = np.full((H, W), 6.0)                       # the viewer's dark surround
    if lit:
        yy, xx = np.mgrid[0:H, 0:W]
        # the face: a broad bright field, brightest near the nose
        img += 60 * np.exp(-((xx - 210) ** 2 + (yy - 120) ** 2) / (2 * 110.0 ** 2))
        cx = PUPIL_C[0] + 6 * np.sin(t / 23.0)       # the eye drifts
        cy = PUPIL_C[1] + 3 * np.cos(t / 31.0)
        rad = 13 + 6 * np.sin(t / 40.0)              # and the pupil breathes
        d = np.hypot(xx - cx, yy - cy)
        img[d < rad + 7] = 42.0                      # the iris: the trough
        img[d < rad] = 250.0                         # the pupil: the saturated plateau
        img += rng.normal(0, 2.0, (H, W))
    else:
        img += rng.normal(0, 1.0, (H, W))            # a dark region is not a black one
    return np.clip(img, 0, 255).astype(np.uint8)


def make_session(n_dark: int = 40, n_lit: int = 120, epochs: int = 2, seed: int = 0):
    """Frames of a session: idle, recording, idle, recording …"""
    rng = np.random.RandomState(seed)
    t = 0
    for _ in range(epochs):
        for _ in range(n_dark):
            yield frame(t, False, rng); t += 1
        for _ in range(n_lit):
            yield frame(t, True, rng); t += 1
    for _ in range(n_dark):
        yield frame(t, False, rng); t += 1


if __name__ == "__main__":
    frames = list(make_session())
    print(f"{len(frames)} frames of {frames[0].shape[1]}x{frames[0].shape[0]}")
    print(f"dark mean {frames[0].mean():.1f}, lit mean {frames[60].mean():.1f}")
