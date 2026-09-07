"""Show the contribution: where the noise scale comes from decides whether background fires.

Three detector variants on the same synthetic recording, arbitrated on the population that
cannot contain events. The middle panel is the mechanism in one picture; the right panel is
the verdict.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, axis_label, use_gallery_style, zero_line
from make_sample import make_sample
from arbitrated import (VARIANTS, arbitrate, calm_window_baseline, detect,
                        noise_sigma_negative_tail)

LABEL = {"dff_direct": "measured trace,\nits own σ",
         "recon_own_sigma": "denoised trace,\nits own σ",
         "arbitrated": "denoised trace,\nσ from the measured one"}
CLIP_K = 3.0


def main() -> None:
    use_gallery_style()
    s = make_sample(seed=0)
    fps = s["fps"]
    t = np.arange(s["dff"].shape[0]) / fps

    # the noisiest background trace: the one a detector is most likely to be fooled by
    bg = np.flatnonzero(~s["is_bouton"])
    j = bg[int(np.argmax([noise_sigma_negative_tail(s["dff"][:, k]) for k in bg]))]
    dffj, recj = s["dff"][:, j], s["reconstruct"][:, j]
    sig_meas = noise_sigma_negative_tail(dffj)
    sig_den = noise_sigma_negative_tail(recj)
    base = calm_window_baseline(recj, fps)
    bar_own = base + CLIP_K * sig_den
    bar_arb = base + CLIP_K * sig_meas
    hits_own = detect("recon_own_sigma", dffj, recj, fps, clip_k=CLIP_K)
    hits_arb = detect("arbitrated", dffj, recj, fps, clip_k=CLIP_K)

    res = arbitrate(s, clip_k=CLIP_K)
    fp = {r["variant"]: r["false_positive_pct"] for r in res}
    real = {r["variant"]: r["real_per_s"] for r in res}
    null = {r["variant"]: r["null_per_s"] for r in res}

    fig, ax = plt.subplots(1, 3, figsize=(12.6, 4.0),
                           gridspec_kw=dict(width_ratios=[1.25, 1.25, 1.0]))

    # a real bouton, for scale
    b = int(np.flatnonzero(s["is_bouton"])[0])
    ax[0].plot(t, s["dff"][:, b], color="#bdbdbd", lw=0.7, label="measured ΔF/F")
    ax[0].plot(t, s["reconstruct"][:, b], color=CAT(1), lw=1.1, label="denoised")
    for fr in s["true_events"][b]:
        ax[0].axvline(fr / fps, color=CAT(2), lw=0.6, alpha=0.55)
    zero_line(ax[0])
    ax[0].set_title("a real bouton (thin lines = true events)", fontsize=9)
    ax[0].set_xlabel(axis_label("time", "s")); ax[0].set_ylabel(axis_label("ΔF/F", "a.u."))
    ax[0].legend(fontsize=7, loc="upper right", framealpha=0.9)

    # the same treatment on background, with both bars
    ax[1].plot(t, dffj, color="#bdbdbd", lw=0.7, label="measured ΔF/F (violent: dim F0)")
    ax[1].plot(t, recj, color=CAT(1), lw=1.1, label="denoised (smooth, plausible)")
    ax[1].axhline(bar_own, color=CAT(4), lw=1.2, ls="--",
                  label=f"bar from the DENOISED σ ({sig_den:.3f})")
    ax[1].axhline(bar_arb, color=CAT(0), lw=1.2,
                  label=f"bar from the MEASURED σ ({sig_meas:.3f})")
    if len(hits_own):
        ax[1].plot(hits_own / fps, recj[hits_own], "v", color=CAT(4), ms=5,
                   label=f"false events: {len(hits_own)}")
    if len(hits_arb):
        ax[1].plot(hits_arb / fps, recj[hits_arb], "v", color=CAT(0), ms=5,
                   label=f"false events: {len(hits_arb)}")
    zero_line(ax[1])
    ax[1].set_title("background: no events exist here", fontsize=9)
    ax[1].set_xlabel(axis_label("time", "s")); ax[1].set_ylabel(axis_label("ΔF/F", "a.u."))
    ax[1].legend(fontsize=6.5, loc="upper right", framealpha=0.9)

    # the verdict
    xs = np.arange(len(VARIANTS))
    cols = [CAT(2), CAT(4), CAT(0)]
    ax[2].bar(xs, [fp[v] for v in VARIANTS], color=cols, width=0.62)
    ax[2].axhline(100, color="#9a9a9a", lw=0.8, ls=":")
    ax[2].text(len(VARIANTS) - 0.5, 103, "fires on background as often\nas on real signal",
               fontsize=6.5, ha="right", va="bottom", color="#666666")
    for x, v in zip(xs, VARIANTS):
        ax[2].text(x, fp[v] + 3, f"{fp[v]:.0f} %", ha="center", fontsize=8)
        ax[2].text(x, -14, f"{real[v]:.2f} vs {null[v]:.2f}/s", ha="center", fontsize=6,
                   color="#666666")
    ax[2].set_xticks(xs); ax[2].set_xticklabels([LABEL[v] for v in VARIANTS], fontsize=7)
    ax[2].set_ylabel("false positives (% of the real rate)")
    ax[2].set_ylim(-20, max(125, max(fp.values()) * 1.15))
    ax[2].set_title(f"arbitrated on the null population (k = {CLIP_K:g})", fontsize=9)

    fig.suptitle("Event detection: peaks on the denoised trace, noise scale from the measured one "
                 "— settled on ROIs that cannot host events", fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = Path(__file__).resolve().parents[1] / "figures" / "before_after.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")
    for v in VARIANTS:
        print(f"  {v:16s} real {real[v]:.3f}/s  null {null[v]:.3f}/s  FP {fp[v]:.1f} %")


if __name__ == "__main__":
    main()
