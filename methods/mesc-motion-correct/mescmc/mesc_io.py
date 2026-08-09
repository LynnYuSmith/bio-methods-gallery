"""Minimal Femtonics **.mesc** read/write for motion correction — layout only, counts untouched.

A .mesc is an HDF5: ``/MSession_i/MUnit_j`` groups, each with a 3-D ``Channel_k`` dataset
``(frames, height, width)`` and acquisition attributes. The one attribute this tool *needs* is the
**pixel size**, ``XAxisConversionConversionLinearScale`` (µm/px) — the correction extent is a
physical distance and is turned into pixels with it, so nothing about the shift limit is hard-coded.

Frames are read and written as the **stored counts** (no PMT/display conversion): registration is a
geometric operation, and the output stays a faithful raw .mesc. The writer copies every source
attribute onto the output so the file remains self-describing, and records what it did.
"""
from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np

PIXEL_SIZE_ATTR = "XAxisConversionConversionLinearScale"   # µm / pixel — the file's own scale
MS_PER_FRAME_ATTR = "ZAxisConversionConversionLinearScale"  # ms / frame → frame rate
# the INTENSITY correction parameter, written straight into the .mesc, per channel:
OFFSET_ATTR = "Channel_{k}_Conversion_ConversionLinearOffset"   # PMT pedestal, e.g. −786 / −1170
DEFAULT_OFFSET = {0: -786.0, 1: -1170.0}                        # fallback only if the attr is absent


def list_units(mesc_path) -> list[dict]:
    """Every unit with its channels, dimensions, and the file-declared pixel size + frame rate."""
    out = []
    with h5py.File(str(mesc_path), "r") as f:
        for sname in sorted(k for k in f.keys() if k.startswith("MSession")):
            for uname in sorted(k for k in f[sname].keys() if k.startswith("MUnit")):
                u = f[f"{sname}/{uname}"]
                a = u.attrs
                channels = sorted(k for k in u.keys() if k.startswith("Channel"))
                ms = float(a.get(MS_PER_FRAME_ATTR, 0) or 0)
                out.append({
                    "session": sname, "unit": uname, "path": f"{sname}/{uname}",
                    "channels": channels,
                    "frames": int(channels and u[channels[0]].shape[0] or 0),
                    "pixel_um": pixel_size_um(mesc_path, f"{sname}/{uname}"),
                    "frame_rate_hz": (1000.0 / ms) if ms > 0 else None,
                })
    return out


def pixel_size_um(mesc_path, unit_path) -> float | None:
    """The recording's pixel size (µm/px), read straight from ``XAxisConversionConversionLinearScale``.

    This is the *correction parameter that lives in the file*: a physical max-shift (µm) is divided
    by it to get the pixel clamp, so the same setting behaves the same on any FOV. Returns None if
    the attribute is absent (the caller must then fall back and say so)."""
    with h5py.File(str(mesc_path), "r") as f:
        v = f[unit_path].attrs.get(PIXEL_SIZE_ATTR)
    return float(v) if v is not None else None


def channel_offset(mesc_path, unit_path, channel) -> float:
    """The intensity correction parameter for a channel — its ``ConversionLinearOffset`` (signed).

    Read straight from the .mesc (``Channel_k_Conversion_ConversionLinearOffset``), NOT hard-coded —
    the PMT pedestal MESc itself subtracts (typically −786 green / −1170 red). Falls back to the PMT
    default for that channel index only if the attribute is missing."""
    k = int(str(channel).split("_")[-1]) if "_" in str(channel) else 0
    with h5py.File(str(mesc_path), "r") as f:
        v = f[unit_path].attrs.get(OFFSET_ATTR.format(k=k))
    return float(v) if v is not None else float(DEFAULT_OFFSET.get(k, 0.0))


def read_channel(mesc_path, unit_path, channel) -> np.ndarray:
    """Stored counts for one unit/channel, ``(frames, H, W)`` — no conversion applied."""
    with h5py.File(str(mesc_path), "r") as f:
        return f[f"{unit_path}/{channel}"][:]


def write_mesc(out_path, source_path, corrected: dict, *, extra_unit_attrs: dict | None = None) -> str:
    """Write a corrected .mesc mirroring ``source_path``'s layout and attributes.

    ``corrected`` is ``{unit_path: {channel: array}}``; any unit/channel absent from it is copied
    through unchanged. Every source attribute is preserved; ``extra_unit_attrs[unit_path]`` (e.g. the
    applied shifts, the pixel size used) is written onto the output unit so the correction is
    self-documenting.
    """
    out_path = Path(out_path)
    extra_unit_attrs = extra_unit_attrs or {}
    with h5py.File(str(source_path), "r") as src, h5py.File(str(out_path), "w") as dst:
        for k, v in src.attrs.items():
            dst.attrs[k] = v
        dst.attrs["motion_corrected"] = True
        dst.attrs["motion_correction_source"] = str(Path(source_path).name)
        for sname in (k for k in src.keys() if k.startswith("MSession")):
            sgrp = dst.create_group(sname)
            for k, v in src[sname].attrs.items():
                sgrp.attrs[k] = v
            for uname in (k for k in src[sname].keys() if k.startswith("MUnit")):
                upath = f"{sname}/{uname}"
                usrc = src[upath]
                ugrp = dst.create_group(upath)
                for k, v in usrc.attrs.items():
                    ugrp.attrs[k] = v
                for k, v in extra_unit_attrs.get(upath, {}).items():
                    ugrp.attrs[k] = v
                for ch in (k for k in usrc.keys() if k.startswith("Channel")):
                    arr = corrected.get(upath, {}).get(ch)
                    data = usrc[ch][:] if arr is None else arr
                    ugrp.create_dataset(ch, data=data, compression="gzip")
    return str(out_path)
