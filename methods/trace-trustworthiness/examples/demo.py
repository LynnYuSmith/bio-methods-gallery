"""Per-ROI residual motion on an already motion-corrected movie, locked to running.

Top: the running trace (bouts shaded). Middle: each bouton's residual in-plane displacement —
small but real, and it rises with every bout, because the field moves non-uniformly and global
correction can't remove all of it per bouton. Bottom: each bouton's presence (how well its patch
still matches its footprint); three stay ~1, but one bouton is shoved out of its ROI during the
strongest bout and its presence collapses to 0 — for those frames the ROI is measuring
background, not the bouton.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, use_gallery_style
from make_sample import make_movie
from tracetrust import assess


def _shade_bouts(ax, run, t, thr=0.3):
    on = run > thr
    edges = np.diff(on.astype(int))
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]
    if on[0]:
        starts = np.r_[0, starts]
    if on[-1]:
        ends = np.r_[ends, len(on) - 1]
    for s, e in zip(starts, ends):
        ax.axvspan(t[s], t[e], color="0.85", zorder=0)


def main():
    use_gallery_style()
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois, fps, run=truth["run"])
    run = truth["run"]
    T = stack.shape[0]
    t = np.arange(T) / fps
    names = list(rois)

    fig, axes = plt.subplots(3, 1, figsize=(9.5, 7), sharex=True, constrained_layout=True)

    axes[0].fill_between(t, run, color=CAT(1), alpha=0.5, lw=0)
    axes[0].set_ylabel("running")
    axes[0].set_title("running (bouts shaded below)", fontsize=10, loc="left")

    for i, name in enumerate(names):
        _shade_bouts(axes[1], run, t)
        axes[1].plot(t, res[name]["displacement"], color=CAT(i), lw=0.8, label=name)
    axes[1].axhline(1.5, color="k", ls=":", lw=0.8)
    axes[1].set_ylabel("residual shift (px)")
    axes[1].set_title("per-bouton residual displacement — rises with each bout", fontsize=10, loc="left")
    axes[1].legend(loc="upper left", fontsize=8, ncol=4)

    for i, name in enumerate(names):
        _shade_bouts(axes[2], run, t)
        r = res[name]
        lbl = f"{name} — DISAPPEARS" if r["disappeared"] else name
        axes[2].plot(t, r["presence"], color=CAT(i), lw=0.9, label=lbl)
    axes[2].axhline(0.4, color="k", ls=":", lw=0.8)
    axes[2].set_ylabel("presence")
    axes[2].set_ylim(-0.05, 1.05)
    axes[2].set_title("per-bouton presence — a bouton pushed out of its ROI collapses to 0",
                      fontsize=10, loc="left")
    axes[2].legend(loc="lower left", fontsize=8, ncol=4)
    axes[2].set_xlabel("time (s)")

    fig.suptitle("Trace trustworthiness: per-ROI residual motion after correction, locked to running",
                 fontsize=12)
    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    for name in names:
        r = res[name]
        print(f"{name}: max_shift {r['max_shift_px']:.1f}px  untrust {r['frac_untrustworthy']:.2f}  "
              f"disappeared {r['disappeared']}  run_corr {r['run_corr']:.2f}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
