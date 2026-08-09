"""Write a synthetic **train** of .mesc repeats of one field of view, with known motion.

The group method's whole point is that *repeat* recordings of one FOV must end on the **same** pixel
grid. So the train shares one static scene, and each repeat gets:

* a **per-repeat baseline offset** (the FOV sat a little differently that run) — repeat 0 has none,
  it is the anchor; and
* **within-repeat drift + jitter**.

Corrected each-to-its-own-reference, the within-repeat motion goes but the baseline offsets survive
(each repeat keeps its own grid). Corrected with the *group* method (one shared reference from repeat
0), every repeat lands on repeat 0's grid — that is what the demo shows. Each file carries the
pixel-size and per-channel intensity-offset (``ConversionLinearOffset``) attributes, so the corrector
reads them from the file.

Returns ground-truth shifts (total = baseline + drift) per repeat, so a corrector can be scored.
"""
import datetime
from pathlib import Path

import h5py
import numpy as np
from scipy.ndimage import shift as nd_shift


def _scene(height, width, rng):
    """A static scene with edges: vessels (ridges) + bright cell blobs — content to lock onto."""
    img = np.full((height, width), 20.0, np.float32)
    yy, xx = np.mgrid[0:height, 0:width]
    for _ in range(4):
        ang, c = rng.uniform(0, np.pi), rng.uniform(0.2, 0.8)
        d = np.abs((xx / width - c) * np.cos(ang) + (yy / height - c) * np.sin(ang))
        img += 120 * np.exp(-(d ** 2) / (2 * 0.012 ** 2))
    for _ in range(8):
        cy, cx = rng.uniform(6, height - 6), rng.uniform(6, width - 6)
        img += rng.uniform(150, 320) * np.exp(-(((yy - cy) ** 2 + (xx - cx) ** 2)
                                                / (2 * rng.uniform(2, 4) ** 2)))
    return img


def _stack(scene, shifts, pedestal, rng):
    frames = len(shifts)
    out = np.empty((frames,) + scene.shape, np.uint16)
    for i, (dy, dx) in enumerate(shifts):
        moved = nd_shift(scene, shift=(dy, dx), order=1, mode="nearest")
        out[i] = np.clip(moved + rng.normal(0, 4, moved.shape) - pedestal, 0, 65535).astype(np.uint16)
    return out


def _write_unit(u, chan_stacks, *, pixel_um, frame_rate_hz, offsets):
    frames, height, width = chan_stacks["Channel_0"].shape
    u.attrs["ZDim"] = frames
    u.attrs["XDim"] = width
    u.attrs["YDim"] = height
    u.attrs["XAxisConversionConversionLinearScale"] = float(pixel_um)
    u.attrs["YAxisConversionConversionLinearScale"] = float(pixel_um)
    u.attrs["ZAxisConversionConversionLinearScale"] = 1000.0 / frame_rate_hz
    u.attrs["MeasurementDatePosix"] = int(datetime.datetime(2026, 1, 1, 12, 0, 0).timestamp())
    for ch, arr in chan_stacks.items():
        k = int(ch.split("_")[-1])
        u.attrs[f"Channel_{k}_Conversion_ConversionLinearOffset"] = float(offsets[k])
        u.attrs[f"Channel_{k}_Conversion_ConversionLinearScale"] = 1.0
        u.create_dataset(ch, data=arr, compression="gzip")


def write_synthetic_train(out_dir, *, n_reps=3, frames=30, height=64, width=64, pixel_um=0.71,
                          frame_rate_hz=31.0, drift_px=4.0, jitter_px=1.0, baseline_px=7.0,
                          offsets=(-786.0, -1170.0), seed=0):
    """Write ``n_reps`` single-unit .mesc repeats of one FOV. Returns dict with paths + ground truth."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(seed)
    scene_g = _scene(height, width, rng)
    scene_r = 0.4 * scene_g
    t = np.linspace(0, 1, frames)

    paths, shifts_per_rep, baselines = [], [], []
    for r in range(n_reps):
        # repeat 0 = anchor (no baseline); later repeats sit a little off
        by, bx = (0.0, 0.0) if r == 0 else (rng.uniform(-baseline_px, baseline_px),
                                            rng.uniform(-baseline_px, baseline_px))
        dy = by + drift_px * np.sin(2 * np.pi * t + r) + rng.normal(0, jitter_px, frames)
        dx = bx + drift_px * np.cos(2 * np.pi * t + r) + rng.normal(0, jitter_px, frames)
        shifts = np.stack([dy, dx], 1).astype(np.float32)

        p = out_dir / f"rep{r}.mesc"
        with h5py.File(str(p), "w") as f:
            u = f.create_group("MSession_0").create_group("MUnit_0")
            _write_unit(u, {"Channel_0": _stack(scene_g, shifts, offsets[0], rng),
                            "Channel_1": _stack(scene_r, shifts, offsets[1], rng)},
                        pixel_um=pixel_um, frame_rate_hz=frame_rate_hz, offsets=offsets)
        paths.append(p); shifts_per_rep.append(shifts); baselines.append((by, bx))

    return {"paths": paths, "shifts": shifts_per_rep, "baselines": baselines,
            "scene_green": scene_g, "pixel_um": pixel_um, "offsets": offsets}


if __name__ == "__main__":
    import tempfile
    t = write_synthetic_train(Path(tempfile.mkdtemp()))
    print(f"wrote {len(t['paths'])} repeats; baselines {[tuple(round(v,1) for v in b) for b in t['baselines']]}")
