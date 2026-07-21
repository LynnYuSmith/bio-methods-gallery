"""Write a few TIFF recordings of one synthetic FOV, each with a different drift."""
from pathlib import Path

import numpy as np
import tifffile


def _fov(y=64, x=64, seed=0):
    """A static scene: a handful of bright blobs (the 'cells')."""
    rng = np.random.RandomState(seed)
    img = np.zeros((y, x), "float32")
    yy, xx = np.mgrid[0:y, 0:x]
    for _ in range(8):
        cy, cx = rng.randint(12, y - 12), rng.randint(12, x - 12)
        img += 200 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * 3.0 ** 2))
    return img


def make_sample(out_dir, n_recordings=3, n_frames=20, seed=0):
    """Write `n_recordings` TIFFs of the same scene, each drifted by its own slow motion + noise."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = _fov(seed=seed)
    rng = np.random.RandomState(seed)
    paths = []
    for r in range(n_recordings):
        drift = rng.uniform(-4, 4, size=2)                 # this recording's own offset
        stack = np.empty((n_frames, *scene.shape), "float32")
        for t in range(n_frames):
            dy = drift[0] + rng.normal(0, 0.6)             # per-frame jitter around the drift
            dx = drift[1] + rng.normal(0, 0.6)
            stack[t] = np.roll(np.roll(scene, int(round(dy)), 0), int(round(dx)), 1)
            stack[t] += rng.normal(0, 8, scene.shape)
        p = out_dir / f"recording_{r}.tif"
        tifffile.imwrite(str(p), stack)
        paths.append(str(p))
    return paths


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    paths = make_sample(here / "raw")
    print("wrote:", [Path(p).name for p in paths])
