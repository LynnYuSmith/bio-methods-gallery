"""A synthetic eye video: a dark pupil that dilates and drifts, a bright corneal glint,
a dark eyelid-corner distractor that swells mid-clip, and a few blink frames.

The point is what a per-frame detector cannot do alone. When the distractor swells it
becomes the largest dark blob, so the naive detector jumps to it; blinks make it drop
out entirely. The ground-truth pupil radius is a smooth signal — recovering it cleanly
is the tracking tool's job.
"""
import numpy as np


def make_eye_video(n_frames: int = 120, h: int = 96, w: int = 128, seed: int = 0):
    """Return ``(frames, truth)`` with frames ``(n_frames, h, w)`` in [0, 1].

    ``truth`` holds the ground-truth pupil ``radius`` (per frame) and the ``blinks``
    frame indices.
    """
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    t = np.arange(n_frames)

    # Ground-truth pupil radius: slow dilation / constriction.
    r_true = 10.0 + 4.0 * np.sin(2 * np.pi * t / 70.0) + 2.0 * np.sin(2 * np.pi * t / 23.0)
    # Pupil centre drifts gently around the middle.
    pcy = h / 2 + 3.0 * np.sin(2 * np.pi * t / 55.0) + rng.normal(0, 0.3, n_frames)
    pcx = w / 2 + 3.0 * np.cos(2 * np.pi * t / 48.0) + rng.normal(0, 0.3, n_frames)

    blinks = set(int(b) for b in rng.choice(np.arange(10, n_frames - 10), size=4, replace=False))

    frames = np.empty((n_frames, h, w), dtype=float)
    for i in range(n_frames):
        img = np.full((h, w), 0.50, dtype=float)                      # iris: mid grey
        pupil = (yy - pcy[i]) ** 2 + (xx - pcx[i]) ** 2 <= r_true[i] ** 2
        img[pupil] = 0.15                                             # pupil: dark

        gy, gx = pcy[i] - r_true[i] * 0.4, pcx[i] + r_true[i] * 0.4   # corneal glint
        img[(yy - gy) ** 2 + (xx - gx) ** 2 <= 2.0 ** 2] = 0.97

        grow = 1.0 + 1.8 * np.exp(-((i - 70) ** 2) / (2 * 8.0 ** 2))  # eyelid-corner blob
        dr = 6.0 * grow                                              # swells around frame 70
        img[(yy - 12) ** 2 + (xx - 16) ** 2 <= dr ** 2] = 0.13

        if i in blinks:                                              # eyelid closed
            img[:] = 0.50
        img += rng.normal(0, 0.02, (h, w))
        frames[i] = np.clip(img, 0.0, 1.0)

    return frames, {"radius": r_true, "blinks": sorted(blinks)}


if __name__ == "__main__":
    fr, truth = make_eye_video()
    print(f"frames {fr.shape}, radius {truth['radius'].min():.1f}-{truth['radius'].max():.1f} px, "
          f"blinks at {truth['blinks']}")
