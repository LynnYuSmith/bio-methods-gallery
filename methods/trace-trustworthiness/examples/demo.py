"""Three boutons after 2-D motion correction — which traces can you trust?

Each row is one bouton's raw fluorescence (the ROI sum). The dashed line is what the resting
level WOULD be under FOV-wide photobleaching alone; the dots are the measured resting level per
time bin. A trustworthy bouton's resting level tracks the dashed line; the z-drifting bouton
plunges below it — its trace reads as going quiet, but the cell never stopped firing, it left
the focal plane. The xy-drifting bouton is caught by tracking its patch (residual shift), not by
the resting level.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, use_gallery_style
from make_sample import make_movie
from tracetrust.trust import assess, roi_trace


VERDICT_COLOR = {"trustworthy": CAT(0), "residual-motion": CAT(1), "z-drift": CAT(3)}


def main():
    use_gallery_style()
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois)
    fov_decline = res["stable"]["fov_decline"]
    order = ["stable", "xy_drift", "z_drift"]
    T = stack.shape[0]
    t = np.arange(T) / fps
    n_bins = len(res["stable"]["resting_f"])
    bin_centres = (np.linspace(0, T, n_bins + 1)[:-1] + T / n_bins / 2) / fps

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7), sharex=True, constrained_layout=True)
    for ax, name in zip(axes, order):
        r = res[name]
        f = roi_trace(stack, rois[name])
        ax.plot(t, f, color=VERDICT_COLOR[r["verdict"]], lw=0.5, alpha=0.9)
        # what the resting level would be under FOV bleaching alone (dashed reference)
        rest0 = r["resting_f"][0]
        ax.plot(t, rest0 * np.exp(np.log(1 - fov_decline) * t / t[-1]),
                "k--", lw=1.2, label="FOV bleaching only")
        ax.plot(bin_centres, r["resting_f"], "o", color="k", ms=4, label="measured resting level")
        ax.set_title(
            f"{name}   —   {r['verdict'].upper()}   "
            f"(residual shift {r['residual_shift_px']:.1f} px · "
            f"resting-level drop {100 * r['frac_decline']:.0f}% vs FOV {100 * fov_decline:.0f}%)",
            fontsize=10, loc="left")
        ax.set_ylabel("raw F")
    axes[0].legend(loc="upper right", fontsize=8, framealpha=0.9)
    axes[-1].set_xlabel("time (s)")
    fig.suptitle("Trace trustworthiness after 2-D motion correction: residual xy motion and z-drift",
                 fontsize=12)

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    for name in order:
        r = res[name]
        print(f"{name:9s} {r['verdict']:16s} shift={r['residual_shift_px']:.2f}px "
              f"z-excess={r['zdrift_excess']:+.2f}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
