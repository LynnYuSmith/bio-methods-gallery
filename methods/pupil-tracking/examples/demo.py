"""What the border buys over the brightest blob, and what the temporal layer buys over neither.

Run:

    python examples/demo.py            # prints the numbers
    python examples/demo.py --figure   # also writes figures/before_after.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pupiltrack import detect_brightest_blob, detect_border, track_pupil  # noqa: E402
from make_sample import make_eye_video  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args()

    frames, truth = make_eye_video()
    r_true = truth["radius"]
    n = len(frames)

    blob = np.array([(detect_brightest_blob(f) or (np.nan,) * 3)[2] for f in frames])
    per_frame = np.array([detect_border(f)["radius"] for f in frames])
    tracked = track_pupil(frames)
    r_track = tracked["radius"]

    def err(a):
        m = np.isfinite(a)
        return (np.nanmedian(np.abs(a[m] - r_true[m])) if m.any() else np.nan, int(m.sum()))

    for name, a in (("brightest blob", blob), ("border, per frame", per_frame),
                    ("border + tracking", r_track)):
        e, k = err(a)
        print(f"  {name:20s} median |error| {e:6.2f} px   on {k:3d}/{n} frames")

    # blinks are excluded: a blink is a different failure, and mixing the two would credit
    # the merge with errors it did not cause
    on_glare = np.array([i for i in truth["glare"] if i not in set(truth["blinks"])])
    if len(on_glare):
        print(f"\n  on the {len(on_glare)} glare frames (blinks excluded):")
        for name, a in (("brightest blob", blob), ("border + tracking", r_track)):
            d = a[on_glare] - r_true[on_glare]
            d = d[np.isfinite(d)]
            if len(d):
                print(f"    {name:20s} bias {np.median(d):+6.2f} px, worst {np.max(np.abs(d)):5.2f}")
    blinks = truth["blinks"]
    kept = [b for b in blinks if np.isfinite(blob[b])]
    print(f"\n  blinks: the blob reports a number on {len(kept)} of {len(blinks)}; "
          f"the border refuses "
          f"{sum(1 for b in blinks if tracked['status'][b] not in ('measured',))} of {len(blinks)}")
    print(f"  transient jumps refused by the temporal layer: {tracked['n_transient_refused']}")

    if args.figure:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 3.4), dpi=150)
        ax.plot(r_true, color="0.15", lw=2.2, label="true radius")
        ax.plot(blob, color="#c0392b", lw=1.2, alpha=0.9, label="brightest blob")
        ax.plot(r_track, color="#2e86c1", lw=1.6, label="border + tracking")
        for b in blinks:
            ax.axvline(b, color="0.85", lw=6, zorder=0)
        if len(on_glare):
            ax.axvspan(on_glare.min(), on_glare.max(), color="#f6e3b4", alpha=0.5, zorder=0,
                       label="lid glare on the pupil")
        ax.set_xlabel("frame"); ax.set_ylabel("pupil radius (px)")
        ax.legend(fontsize=8, frameon=False, ncol=4)
        ax.spines[["top", "right"]].set_visible(False)
        out = Path(__file__).resolve().parents[1] / "figures" / "before_after.png"
        fig.tight_layout(); fig.savefig(out)
        print(f"\n  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
