"""A synthetic bright-pupil eye video, built to contain the failure this tile is about.

Under coaxial infrared illumination the pupil is the BRIGHT structure: a saturated plateau with
a sharp fall into the darker iris. The clip below has

* a pupil that dilates and constricts smoothly and drifts a little, with a saturated plateau;
* a **lid-glare band** that brightens and slides across the top of the pupil around the middle
  of the clip. Where it touches, the pupil and the glare become one bright region — this is the
  whole point. A detector that reports the area of the largest bright blob reads the merged
  region as a larger pupil, and the error looks exactly like a dilation;
* a small specular glint inside the pupil, which is brighter still and must not be mistaken for
  the border;
* a few blink frames, where there is no pupil to measure at all.

The ground-truth radius is a smooth signal. Recovering it — and refusing the blinks instead of
inventing numbers for them — is what the tile demonstrates.
"""
import numpy as np


def make_eye_video(n_frames: int = 140, h: int = 96, w: int = 128, seed: int = 0):
    """Return ``(frames, truth)`` with frames ``(n_frames, h, w)`` in grey levels 0-255.

    ``truth`` holds the ground-truth pupil ``radius`` per frame, the ``blinks`` frame indices
    and the ``glare`` frames where the lid band overlaps the pupil.
    """
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:h, 0:w]
    t = np.arange(n_frames)

    r_true = 13.0 + 4.0 * np.sin(2 * np.pi * t / 80.0) + 1.5 * np.sin(2 * np.pi * t / 27.0)
    pcy = h / 2 + 2.5 * np.sin(2 * np.pi * t / 60.0) + rng.normal(0, 0.25, n_frames)
    pcx = w / 2 + 3.0 * np.cos(2 * np.pi * t / 52.0) + rng.normal(0, 0.25, n_frames)

    blinks = sorted(int(b) for b in rng.choice(np.arange(12, n_frames - 12), 4, replace=False))
    # the glare band grows and shrinks around frame 70 and hangs just above the pupil
    glare_amp = 205.0 * np.exp(-((t - 70) ** 2) / (2 * 11.0 ** 2))

    frames = np.empty((n_frames, h, w), dtype=float)
    overlapping = []
    for i in range(n_frames):
        img = np.full((h, w), 60.0)                                   # iris: dark
        img += 12.0 * np.exp(-((yy - h) ** 2) / (2 * 30.0 ** 2))      # a soft lid shadow

        d2 = (yy - pcy[i]) ** 2 + (xx - pcx[i]) ** 2
        pupil = d2 <= r_true[i] ** 2
        img[pupil] = 235.0                                            # the saturated plateau
        # a soft border a pixel wide, so the half-drop has something to land on
        ring = (d2 > r_true[i] ** 2) & (d2 <= (r_true[i] + 1.6) ** 2)
        img[ring] = 150.0

        gy = pcy[i] - r_true[i] - 1.0                                 # the lid-glare band
        band = np.exp(-((yy - gy) ** 2) / (2 * 3.5 ** 2))
        img += glare_amp[i] * band
        # 'overlapping' = the band is bright enough to threshold together with the
        # pupil, which is when the two become ONE bright region
        if glare_amp[i] * band.max() > 150:
            overlapping.append(i)

        glint_y, glint_x = pcy[i] - r_true[i] * 0.35, pcx[i] + r_true[i] * 0.35
        img[(yy - glint_y) ** 2 + (xx - glint_x) ** 2 <= 1.8 ** 2] = 255.0

        if i in blinks:                                               # the lid is closed
            img[:] = 70.0 + 18.0 * np.exp(-((yy - h / 2) ** 2) / (2 * 22.0 ** 2))

        img += rng.normal(0, 2.0, (h, w))
        frames[i] = np.clip(img, 0, 255)

    return frames, {"radius": r_true, "blinks": blinks, "glare": overlapping}


if __name__ == "__main__":
    fr, truth = make_eye_video()
    print(f"frames {fr.shape}, radius {truth['radius'].min():.1f}-{truth['radius'].max():.1f} px")
    print(f"blinks at {truth['blinks']}, glare overlapping the pupil on "
          f"{len(truth['glare'])} frames")
