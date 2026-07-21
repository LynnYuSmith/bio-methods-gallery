"""Read a set of TIFF recordings, group-correct them, write TIFF and a master-like HDF5.

The HDF5 layout mirrors the served-report tile so the two compose: one shared reference, and per
recording its registered frames and its per-frame shifts.

    /reference                       (y, x) float; the shared reference image
    /units/<name>/frames             (frames, y, x) float; the registered stack
    /units/<name>/motion_shifts      (frames, 2) float; per-frame (dy, dx)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile

from .register import group_motion_correct


def _stem(p: Path) -> str:
    return p.stem


def correct_tiffs(tiff_paths, out_dir, hdf5_name: str = "group_corrected.h5"):
    """Group-correct a list of TIFF recordings of one FOV; write registered TIFFs + one HDF5.

    Parameters
    ----------
    tiff_paths
        The recordings, in order; the first one gives the shared reference.
    out_dir
        Where to write ``<name>_registered.tif`` per recording and ``hdf5_name``.
    """
    tiff_paths = [Path(p) for p in tiff_paths]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stacks = [np.asarray(tifffile.imread(str(p)), dtype="float32") for p in tiff_paths]
    stacks = [s[None] if s.ndim == 2 else s for s in stacks]      # a single-frame TIFF -> (1, y, x)
    names = [_stem(p) for p in tiff_paths]

    registered, ref, shifts = group_motion_correct(stacks)

    write_tiffs(out_dir, names, registered)
    h5_path = out_dir / hdf5_name
    write_hdf5(h5_path, names, registered, ref, shifts)
    return {"hdf5": str(h5_path),
            "tiffs": [str(out_dir / f"{n}_registered.tif") for n in names],
            "reference_shape": list(ref.shape)}


def write_tiffs(out_dir, names, registered) -> None:
    """Write one ``<name>_registered.tif`` per recording."""
    out_dir = Path(out_dir)
    for name, stack in zip(names, registered):
        tifffile.imwrite(str(out_dir / f"{name}_registered.tif"),
                         stack.astype("float32"))


def write_hdf5(path, names, registered, ref, shifts) -> None:
    """Write the master-like HDF5 (shared reference, per-recording frames + shifts)."""
    import h5py
    with h5py.File(str(path), "w") as f:
        f.create_dataset("reference", data=np.asarray(ref, "float32"))
        for name, stack, sh in zip(names, registered, shifts):
            g = f.create_group(f"units/{name}")
            g.create_dataset("frames", data=stack.astype("float32"),
                             compression="gzip", compression_opts=1)
            g.create_dataset("motion_shifts", data=np.asarray(sh, "float32"))
