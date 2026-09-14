#!/usr/bin/env python3
"""What the gate is for: the same detector, with and without it.

Run me:  python examples/demo.py

A pupil detector handed a dark frame does not refuse it. It finds the brightest thing there —
sensor noise — and reports a diameter with a confidence, and afterwards nothing can tell those
numbers from a genuinely constricted pupil. The gate turns that into a gap.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_sample import make_session                     # noqa: E402
from pupilscreen import LaserGate, Roi, RoiSet, profile_health, run_stream   # noqa: E402


def naive_diameter(crop: np.ndarray) -> dict:
    """A stand-in detector: the equivalent radius of whatever is brightest.

    It is deliberately the obvious one, because the point is what it does when handed nothing.
    """
    a = np.asarray(crop, float)
    thr = a.max() * 0.6
    n = int((a >= thr).sum())
    return {"diameter": float(2 * np.sqrt(max(n, 1) / np.pi)), "status": "ok"}


def main() -> int:
    rois = RoiSet([Roi("pupil", (110, 55, 200, 140)), Roi("laser", (10, 10, 90, 60))])
    u = rois.union()
    # run_stream is fed grabs of the UNION, not whole screens: on a real desktop you capture
    # that one rectangle and nothing else, and the regions are cut from it.
    frames = [f[u[1]:u[3], u[0]:u[2]] for f in make_session()]

    gated = list(run_stream(frames, rois, naive_diameter))
    ungated = list(run_stream(frames, rois, naive_diameter, gate=LaserGate(override=True)))

    dark = [i for i, r in enumerate(gated) if r["status"] == "laser_off"]
    measured_in_dark = [ungated[i]["diameter"] for i in dark]
    real = [r["diameter"] for r in gated if r["status"] == "ok"]

    print(f"  {len(frames)} frames, {len(dark)} of them with the rig idle\n")
    print("  without the gate, the idle frames are measured anyway:")
    print(f"    {len(measured_in_dark)} 'measurements' of darkness, "
          f"median {np.median(measured_in_dark):.1f} px, "
          f"range {min(measured_in_dark):.1f}-{max(measured_in_dark):.1f}")
    print(f"    real pupils in the same session: median {np.median(real):.1f} px, "
          f"range {min(real):.1f}-{max(real):.1f}")
    overlap = sum(1 for v in measured_in_dark if min(real) <= v <= max(real))
    # Say what the numbers say. Whether a fabricated value happens to look plausible depends
    # on the detector: this stand-in reads noise as a huge pupil, a threshold-based one reads
    # it as a tiny one and lands squarely inside the real range. What is true of both is that
    # the row carries a diameter and a status of "ok", and nothing downstream can tell it from
    # a measurement.
    print(f"    {overlap} of the {len(measured_in_dark)} land inside the real range"
          + (" — those are indistinguishable from a real pupil afterwards"
             if overlap else ", though every one of them is reported as a measurement") + "\n")
    print("  with the gate, those frames are gaps:")
    print(f"    {len(dark)} rows of status=laser_off, {len(real)} measurements, "
          f"{gated[-1]['epoch']} recording epochs found\n")

    # A frame the gate itself called lit — the middle of the session is an idle stretch, and
    # picking it by index would have reported the profile of a dark region as if it were the
    # pupil's.
    lit_i = next(i for i, r in enumerate(gated) if r["status"] == "ok")
    crop = rois.of_role("pupil")[0].crop(frames[lit_i], origin=(u[0], u[1]))
    h = profile_health(crop)
    print(f"  profile on a lit frame: plateau {h['plateau']:.0f}, trough {h['trough']:.0f}, "
          f"contrast {h['contrast']:.0f}")
    print("  compare these with the same numbers from the recorded video: if they disagree,")
    print("  the display is rewriting the profile and the screen is not showing you the data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
