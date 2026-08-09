"""Group (concat) motion correction for a **train** of .mesc repeats → corrected .mesc out.

This is *our* method, not per-file registration. Repeat recordings of one field of view drift apart
if each is corrected to its own reference. Instead:

1. build **one shared reference** from the **first** unit of the train (the early-tissue anchor —
   later repeats have already deformed, so the anchor must come from the start);
2. **hand that reference** to the correction of *every* unit in the concatenated train, so every
   frame of every repeat is registered to the *same* pixel grid;
3. split back and write each repeat as a corrected .mesc.

Registration runs on the **green** channel (``Channel_0``) with its **intensity correction read from
the file** — the PMT offset ``Channel_0_Conversion_ConversionLinearOffset`` (−786…), subtracted so the
background sits at zero and the reference/phase-correlation lock onto tissue, not the pedestal. The
same shift is applied to every channel. Output frames stay in native counts, conversion attrs
preserved.

The production pipeline runs this as **concat-MC over Suite2p** (``force_refImg`` = the first unit's
reference); here is a compact, dependency-light independent implementation of the same idea, whose
extra contribution is the faithful **.mesc → .mesc** round-trip.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from . import mesc_io
from .register import apply_shift, build_reference, estimate_shift, _clamp

DEFAULT_MAX_SHIFT_UM = 20.0   # physical registration ceiling → pixels via the file's pixel size


def _registration_frames(mesc_path, unit_path, channel):
    """Green frames with the file's intensity offset removed (background → 0) — the registration input.

    The offset is the *intensity correction parameter written in the .mesc*; reading it (not
    assuming −786) is the point. Returns ``(frames_f32, offset)``."""
    raw = mesc_io.read_channel(mesc_path, unit_path, channel).astype(np.float32)
    off = mesc_io.channel_offset(mesc_path, unit_path, channel)
    return np.clip(raw + off, 0.0, None), off


def build_group_reference(train, *, register_channel="Channel_0",
                          max_shift_um=DEFAULT_MAX_SHIFT_UM, sigma=4.0, warn=True) -> np.ndarray:
    """The shared reference for the whole train — a refined mean of the **first** unit only.

    ``train`` is an ordered list of ``(mesc_path, unit_path)``; index 0 is the early anchor. This
    reference is what you hand to :func:`correct_train`."""
    mesc_path, unit_path = train[0]
    px = mesc_io.pixel_size_um(mesc_path, unit_path) or 1.0
    max_shift_px = max_shift_um / px
    frames, off = _registration_frames(mesc_path, unit_path, register_channel)
    if warn:
        warnings.warn(
            f"[mescmc] shared reference from the FIRST unit {unit_path} (early-tissue anchor); "
            f"intensity offset {off:g} read from the file; max shift {max_shift_um:g} µm "
            f"= {max_shift_px:.1f} px at {px:g} µm/px.", stacklevel=2)
    return build_reference(frames, sigma=sigma, max_shift_px=max_shift_px)


def correct_train(train, reference, *, register_channel="Channel_0",
                  max_shift_um=DEFAULT_MAX_SHIFT_UM, sigma=4.0, warn=True) -> list[dict]:
    """Register every unit of the train to the **passed** shared ``reference``.

    Returns a list (one per unit) of ``{channel: corrected_stack, 'shifts':…, 'pixel_um':…,
    'offset':…}``. The green channel yields the shifts; the same shift is applied to all channels
    (they are one scan). Frames are corrected in native counts."""
    results = []
    for mesc_path, unit_path in train:
        units = {u["path"]: u for u in mesc_io.list_units(mesc_path)}
        channels = units[unit_path]["channels"]
        reg_ch = register_channel if register_channel in channels else channels[0]
        px = units[unit_path]["pixel_um"] or 1.0
        max_shift_px = max_shift_um / px

        reg_frames, off = _registration_frames(mesc_path, unit_path, reg_ch)
        shifts = np.empty((len(reg_frames), 2), np.float32)
        for i, fr in enumerate(reg_frames):
            dy, dx = estimate_shift(reference, fr, sigma=sigma)
            shifts[i] = _clamp(dy, dx, max_shift_px)

        res = {"unit_path": unit_path, "mesc_path": str(mesc_path), "shifts": shifts,
               "pixel_um": px, "offset": off, "register_channel": reg_ch}
        for ch in channels:                       # apply the SAME shift to every channel, native counts
            raw = mesc_io.read_channel(mesc_path, unit_path, ch)
            out = np.empty_like(raw)
            for i in range(len(raw)):
                out[i] = apply_shift(raw[i], float(shifts[i, 0]), float(shifts[i, 1]))
            res[ch] = out
        if warn:
            warnings.warn(f"[mescmc] {unit_path}: registered to the shared reference, "
                          f"mean |shift| {np.hypot(*shifts.T).mean():.2f} px, applied to {channels}.",
                          stacklevel=2)
        results.append(res)
    return results


def group_motion_correct_mesc(in_paths, out_dir, *, register_channel="Channel_0",
                              max_shift_um=DEFAULT_MAX_SHIFT_UM, sigma=4.0, warn=True) -> list[str]:
    """Correct a train of .mesc files against ONE shared reference; write ``<stem>_MC.mesc`` each.

    ``in_paths`` is the ordered train (one or more .mesc, each possibly multi-unit). The shared
    reference is built from the very first unit of the first file and handed to the whole train.
    Returns the written output paths."""
    in_paths = [Path(p) for p in in_paths]
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)

    # the concatenated train: every unit of every file, in order
    train = [(p, u["path"]) for p in in_paths for u in mesc_io.list_units(p)]
    if not train:
        raise ValueError("no MESc units found in the input train")

    reference = build_group_reference(train, register_channel=register_channel,
                                      max_shift_um=max_shift_um, sigma=sigma, warn=warn)
    corrected = correct_train(train, reference, register_channel=register_channel,
                              max_shift_um=max_shift_um, sigma=sigma, warn=warn)

    # regroup corrected units by their source file and write one _MC.mesc per input
    by_file: dict = {}
    for res in corrected:
        by_file.setdefault(res["mesc_path"], {})[res["unit_path"]] = res
    written = []
    for p in in_paths:
        per_unit = by_file.get(str(p), {})
        frames = {upath: {ch: r[ch] for ch in r if ch.startswith("Channel")}
                  for upath, r in per_unit.items()}
        extra = {upath: {"motion_correction_shifts_yx": r["shifts"],
                         "motion_correction_offset": r["offset"],
                         "motion_correction_shared_reference": True,
                         "motion_correction_register_channel": r["register_channel"]}
                 for upath, r in per_unit.items()}
        out = out_dir / f"{p.stem}_MC.mesc"
        mesc_io.write_mesc(out, p, frames, extra_unit_attrs=extra)
        written.append(str(out))
    return written
