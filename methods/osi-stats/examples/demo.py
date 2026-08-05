"""Show the contribution: a bare OSI threshold vs an honest call (Rayleigh + FDR).

Left — the OSI point estimate is positively biased, so a threshold (OSI > 0.33) flags a
crowd of genuinely UNTUNED boutons as tuned. Right — the Rayleigh p-value with
Benjamini-Hochberg FDR across the population separates the real tuning from the bias."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import axis_label, use_gallery_style
from make_sample import make_population
from osistats import classify_population

TUNED_C, UNTUNED_C = "#6b7f9e", "#9e7b8a"   # muted slate / mauve


def main() -> None:
    use_gallery_style()
    _M, T, truth, ori = make_population()
    r = classify_population(T, ori, osi_thr=0.33, alpha=0.05)
    osis, qvals = r["osi"], r["qval"]
    naive, honest = r["naive"], r["honest"]

    fp_naive = int(np.sum(naive & ~truth))       # untuned called tuned
    fp_honest = int(np.sum(honest & ~truth))
    tp_naive = int(np.sum(naive & truth))
    tp_honest = int(np.sum(honest & truth))
    neglogq = -np.log10(np.clip(qvals, 1e-6, 1))

    fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.8))

    # Left: OSI histogram, truth-coloured, with the naive threshold.
    bins = np.linspace(0, 1, 26)
    ax[0].hist(osis[~truth], bins=bins, color=UNTUNED_C, alpha=0.85, label="untuned (truth)")
    ax[0].hist(osis[truth], bins=bins, color=TUNED_C, alpha=0.85, label="tuned (truth)")
    ax[0].axvline(0.33, color="#3b3b3b", lw=1.2, ls="--")
    ax[0].text(0.34, ax[0].get_ylim()[1] * 0.9, "OSI > 0.33\n→ naive 'tuned'", fontsize=7)
    ax[0].set_xlabel(axis_label("OSI"))
    ax[0].set_ylabel(axis_label("boutons"))
    ax[0].set_title(f"naive threshold: {fp_naive} untuned boutons flagged", fontsize=9)
    ax[0].legend(fontsize=7, loc="upper right")

    # Right: OSI vs FDR significance; horizontal line = q = 0.05.
    ax[1].scatter(osis[~truth], neglogq[~truth], s=14, color=UNTUNED_C, label="untuned (truth)")
    ax[1].scatter(osis[truth], neglogq[truth], s=16, color=TUNED_C, label="tuned (truth)")
    ax[1].axhline(-np.log10(0.05), color="#3b3b3b", lw=1.2, ls="--")
    ax[1].text(0.02, -np.log10(0.05) + 0.1, "FDR q = 0.05", fontsize=7)
    ax[1].set_xlabel(axis_label("OSI"))
    ax[1].set_ylabel(axis_label("−log₁₀ q (shuffle + BH-FDR)"))
    ax[1].set_title(f"shuffle test + FDR: {fp_honest} untuned flagged", fontsize=9)
    ax[1].legend(fontsize=7, loc="upper left")

    fig.suptitle("orientation tuning, called honestly: a shuffle test with FDR controls the "
                 "false positives a bare OSI threshold lets through", fontsize=9)
    fig.tight_layout()

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)

    print(f"truly tuned: {int(truth.sum())}/{len(truth)}")
    print(f"naive (OSI>0.33):     {tp_naive} true positives, {fp_naive} FALSE positives")
    print(f"shuffle test + FDR:   {tp_honest} true positives, {fp_honest} FALSE positives")


if __name__ == "__main__":
    main()
