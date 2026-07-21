"""Write a tiny sample master file in the served layout (used by the demo and the tests)."""
from pathlib import Path

import h5py
import numpy as np


def make_sample(path: str, n_frames: int = 300, n_rois: int = 4, seed: int = 0) -> str:
    """Write a minimal experiment: one area, one unit, dF/F traces, and ROI polygons."""
    rng = np.random.RandomState(seed)
    names = [f"Mean{i}" for i in range(2, 2 + n_rois)]
    dff = rng.standard_normal((n_frames, n_rois)).astype("float32") * 0.05
    for r in range(n_rois):                       # a few transients per ROI
        for onset in rng.randint(20, n_frames - 20, size=5):
            dff[onset:onset + 8, r] += np.linspace(0.6, 0.0, 8)

    with h5py.File(path, "w") as f:
        m = f.create_group("metadata")
        m.attrs["experiment_id"] = "sample"
        m.attrs["indicator"] = "GCaMP"
        u = f.create_group("units/MUnit_0")
        u.create_dataset("roi_names", data=np.array(names, dtype=object),
                         dtype=h5py.string_dtype())
        u.create_group("traces").create_dataset("dff", data=dff)
        polys = f.create_group("groups/Area1/polygons")
        for i, nm in enumerate(names):            # small square ROIs
            x, y = 10 + 20 * i, 10
            polys.create_dataset(nm, data=np.array(
                [[x, y], [x + 8, y], [x + 8, y + 8], [x, y + 8]], dtype="float32"))
    return path


if __name__ == "__main__":
    out = str(Path(__file__).resolve().parent / "sample_master.h5")
    make_sample(out)
    print(f"wrote {out}")
