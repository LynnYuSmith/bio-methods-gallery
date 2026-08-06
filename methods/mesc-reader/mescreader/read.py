"""Read a Femtonics .mesc file and convert it to TIFF or HDF5.

A .mesc is an HDF5: ``/MSession_i/MUnit_j`` groups, each with acquisition attributes and one 3-D
dataset per channel, ``Channel_k`` of shape ``(frames, height, width)``.

Each channel carries a **linear display conversion** in its attributes — a scale and an offset —
that the native Femtonics reader applies to turn the stored counts into displayed values:
``physical = stored × ConversionLinearScale + ConversionLinearOffset`` (clipped at 0). The offset
is the PMT dark-current baseline (typically **−786** for green / Channel_0 and **−1170** for red /
Channel_1). A reader that ignores it returns numbers ~786–1170 too high — NOT what a collaborator
sees in MESc.

So this **applies that conversion by default**, per channel, and says so **loudly** (which offset
it used, on which channel). You can override the coefficients by hand, or pass
``apply_conversion=False`` for the truly-stored counts. What it never does is any *processing* —
no motion correction, no background subtraction, no rescaling beyond the file's own stated
conversion.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import h5py
import numpy as np

# PMT-offset fallbacks if a channel's conversion attr is missing (signed, as the reader applies).
DEFAULT_OFFSET = {0: -786, 1: -1170}


def _decode(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="ignore")
    if isinstance(v, np.ndarray) and v.dtype.kind in "SU":
        return v.astype(str).tolist()
    return v


def _channel_index(channel: str) -> int:
    try:
        return int(str(channel).split("_")[-1])
    except ValueError:
        return 0


def channel_conversion(mesc_path, unit_path, channel="Channel_0") -> tuple[float, float]:
    """The stored linear display conversion for a channel → ``(scale, offset)`` (offset signed).

    ``physical = stored × scale + offset``. Reads ``Channel_k_Conversion_ConversionLinearScale`` /
    ``…LinearOffset`` from the unit's attrs; falls back to scale 1.0 and the PMT default offset
    (−786 green / −1170 red) if an attr is absent."""
    k = _channel_index(channel)
    with h5py.File(str(mesc_path), "r") as f:
        a = f[unit_path].attrs
        s = a.get(f"Channel_{k}_Conversion_ConversionLinearScale")
        o = a.get(f"Channel_{k}_Conversion_ConversionLinearOffset")
    scale = float(s) if s is not None else 1.0
    offset = float(o) if o is not None else float(DEFAULT_OFFSET.get(k, 0))
    return scale, offset


def list_units(mesc_path) -> list[dict]:
    """List every unit with its acquisition summary and per-channel conversion coefficients."""
    out = []
    with h5py.File(str(mesc_path), "r") as f:
        for sname in sorted(k for k in f.keys() if k.startswith("MSession")):
            sess = f[sname]
            for uname in sorted(k for k in sess.keys() if k.startswith("MUnit")):
                u = sess[uname]
                a = u.attrs
                z_scale = float(a.get("ZAxisConversionConversionLinearScale", 0) or 0)
                channels = sorted(k for k in u.keys() if k.startswith("Channel"))
                path = f"{sname}/{uname}"
                out.append({
                    "session": sname, "unit": uname, "path": path, "channels": channels,
                    "frames": int(a.get("ZDim", channels and u[channels[0]].shape[0] or 0)),
                    "height": int(a.get("YDim", 0)), "width": int(a.get("XDim", 0)),
                    "frame_rate_hz": (1000.0 / z_scale) if z_scale > 0 else None,
                    "pixel_um": _decode(a.get("XAxisConversionConversionLinearScale")),
                    "conversion": {ch: channel_conversion(mesc_path, path, ch) for ch in channels},
                })
    return out


def read_metadata(mesc_path, unit_path) -> dict:
    """Every stored attribute of a unit, decoded to plain Python — nothing interpreted."""
    with h5py.File(str(mesc_path), "r") as f:
        return {k: _decode(v) for k, v in f[unit_path].attrs.items()}


def read_frames(mesc_path, unit_path, channel="Channel_0", *, apply_conversion: bool = True,
                scale: float | None = None, offset: float | None = None,
                warn: bool = True) -> np.ndarray:
    """Frames for one unit/channel, ``(frames, height, width)``.

    By default the channel's stored linear conversion is **applied** (``stored × scale + offset``,
    clipped at 0) and a **loud warning** names the coefficients used — otherwise the counts are
    ~786–1170 too high versus what MESc shows. Override ``scale`` / ``offset`` to set them by hand,
    or pass ``apply_conversion=False`` for the raw stored counts (no conversion, no warning)."""
    with h5py.File(str(mesc_path), "r") as f:
        raw = f[f"{unit_path}/{channel}"][:]
    if not apply_conversion:
        return raw

    s0, o0 = channel_conversion(mesc_path, unit_path, channel)
    s = s0 if scale is None else float(scale)
    o = o0 if offset is None else float(offset)
    if warn:
        src = "set by hand" if (scale is not None or offset is not None) else "read from the file"
        warnings.warn(
            f"[mesc-reader] APPLIED the MESc display conversion to {unit_path}/{channel}: "
            f"physical = stored*{s:g} + ({o:g})  [coefficients {src}]. The stored counts are "
            f"~{abs(o):g} higher; pass apply_conversion=False for them.",
            stacklevel=2)
    phys = np.clip(raw.astype(np.float64) * s + o, 0.0, None)
    if float(s) == 1.0 and float(o).is_integer():
        return phys.astype(raw.dtype)                 # stays integer counts (scale 1, integer offset)
    return phys.astype(np.float32)


def _convert_meta(u, ch, apply_conversion, scale, offset):
    s, o = u["conversion"][ch]
    if not apply_conversion:
        return {"conversion_applied": False}
    return {"conversion_applied": True,
            "conversion_scale": s if scale is None else float(scale),
            "conversion_offset": o if offset is None else float(offset)}


def mesc_to_tiff(mesc_path, out_dir, *, apply_conversion: bool = True, scale=None, offset=None,
                 warn: bool = True) -> list[str]:
    """Write one TIFF stack per unit/channel into ``out_dir`` (conversion applied by default).

    The acquisition metadata + whether/what conversion was applied go into each TIFF's ImageJ
    description, so the stack stays self-describing."""
    import tifffile
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for u in list_units(mesc_path):
        for ch in u["channels"]:
            arr = read_frames(mesc_path, u["path"], ch, apply_conversion=apply_conversion,
                              scale=scale, offset=offset, warn=warn)
            name = f"{u['session']}_{u['unit']}_{ch}.tif"
            meta = {"fps": u["frame_rate_hz"], "unit": u["path"], "channel": ch,
                    "pixel_um": u["pixel_um"], **_convert_meta(u, ch, apply_conversion, scale, offset)}
            tifffile.imwrite(out_dir / name, arr, imagej=True, metadata=meta)
            written.append(str(out_dir / name))
    return written


def mesc_to_hdf5(mesc_path, out_path, *, apply_conversion: bool = True, scale=None, offset=None,
                 warn: bool = True) -> str:
    """Write a plain HDF5 mirror: ``/<unit>/<channel>`` datasets + unit attrs (conversion applied
    by default; the applied coefficients are recorded on each dataset)."""
    out_path = Path(out_path)
    units = list_units(mesc_path)
    with h5py.File(str(mesc_path), "r") as src, h5py.File(str(out_path), "w") as dst:
        dst.attrs["source"] = str(Path(mesc_path).name)
        dst.attrs["conversion_applied"] = bool(apply_conversion)
        for u in units:
            g = dst.create_group(u["path"])
            for k, v in src[u["path"]].attrs.items():
                g.attrs[k] = v
            for ch in u["channels"]:
                arr = read_frames(mesc_path, u["path"], ch, apply_conversion=apply_conversion,
                                  scale=scale, offset=offset, warn=warn)
                d = g.create_dataset(ch, data=arr, compression="gzip")
                for mk, mv in _convert_meta(u, ch, apply_conversion, scale, offset).items():
                    d.attrs[mk] = mv
    return str(out_path)
