"""Read a Femtonics .mesc file and convert it, RAW, to TIFF or HDF5 — no correction, nothing.

A .mesc is an HDF5: ``/MSession_i/MUnit_j`` groups, each with acquisition attributes and one 3-D
dataset per channel, ``Channel_k`` of shape ``(frames, height, width)``. This reads the frames
exactly as stored (the stored integer counts, no PMT-offset, no motion correction, no scaling)
and writes them out unchanged, carrying the acquisition metadata alongside so nothing is lost.

The per-channel linear conversion (``..._ConversionLinearOffset`` / scale) is *reported* in the
metadata but NOT applied — "as-is" means the stored values.
"""
from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np


def _decode(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="ignore")
    if isinstance(v, np.ndarray) and v.dtype.kind in "SU":
        return v.astype(str).tolist()
    return v


def list_units(mesc_path) -> list[dict]:
    """List every unit in the file with its acquisition summary (from the stored attributes)."""
    out = []
    with h5py.File(str(mesc_path), "r") as f:
        for sname in sorted(k for k in f.keys() if k.startswith("MSession")):
            sess = f[sname]
            for uname in sorted(k for k in sess.keys() if k.startswith("MUnit")):
                u = sess[uname]
                a = u.attrs
                z_scale = float(a.get("ZAxisConversionConversionLinearScale", 0) or 0)
                channels = sorted(k for k in u.keys() if k.startswith("Channel"))
                out.append({
                    "session": sname, "unit": uname, "path": f"{sname}/{uname}",
                    "channels": channels,
                    "frames": int(a.get("ZDim", channels and u[channels[0]].shape[0] or 0)),
                    "height": int(a.get("YDim", 0)), "width": int(a.get("XDim", 0)),
                    "frame_rate_hz": (1000.0 / z_scale) if z_scale > 0 else None,
                    "pixel_um": _decode(a.get("XAxisConversionConversionLinearScale")),
                })
    return out


def read_metadata(mesc_path, unit_path) -> dict:
    """Every stored attribute of a unit, decoded to plain Python — nothing interpreted."""
    with h5py.File(str(mesc_path), "r") as f:
        return {k: _decode(v) for k, v in f[unit_path].attrs.items()}


def read_frames(mesc_path, unit_path, channel="Channel_0") -> np.ndarray:
    """The raw ``(frames, height, width)`` array for one unit/channel — exactly as stored."""
    with h5py.File(str(mesc_path), "r") as f:
        return f[f"{unit_path}/{channel}"][:]


def mesc_to_tiff(mesc_path, out_dir) -> list[str]:
    """Write one raw TIFF stack per unit/channel into ``out_dir``. Returns the written paths.

    The acquisition metadata (frame rate, pixel size, dimensions) is stored in each TIFF's
    ImageJ description so the stack stays self-describing."""
    import tifffile
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for u in list_units(mesc_path):
        for ch in u["channels"]:
            arr = read_frames(mesc_path, u["path"], ch)
            name = f"{u['session']}_{u['unit']}_{ch}.tif"
            meta = {"fps": u["frame_rate_hz"], "unit": u["path"], "channel": ch,
                    "pixel_um": u["pixel_um"]}
            tifffile.imwrite(out_dir / name, arr, imagej=True, metadata=meta)
            written.append(str(out_dir / name))
    return written


def mesc_to_hdf5(mesc_path, out_path) -> str:
    """Write a plain HDF5 mirroring the raw frames: ``/<unit>/<channel>`` datasets + unit attrs.

    Same data, standard layout, readable by any HDF5 tool — the metadata attributes travel with
    each unit group. Nothing is corrected or rescaled."""
    out_path = Path(out_path)
    with h5py.File(str(mesc_path), "r") as src, h5py.File(str(out_path), "w") as dst:
        dst.attrs["source"] = str(Path(mesc_path).name)
        dst.attrs["note"] = "raw frames from a .mesc, unmodified (no correction, no scaling)"
        for u in list_units(mesc_path):
            g = dst.create_group(u["path"])
            for k, v in src[u["path"]].attrs.items():
                g.attrs[k] = v
            for ch in u["channels"]:
                g.create_dataset(ch, data=src[f"{u['path']}/{ch}"][:], compression="gzip")
    return str(out_path)
