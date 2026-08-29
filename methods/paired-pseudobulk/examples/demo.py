"""Score the two normalisations against a planted truth, and draw the before/after."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from make_sample import REFERENCE_GENE, make_sample          # noqa: E402
from pairedpb import paired_log2fc, paired_test, top_gene_share  # noqa: E402


def score(result, truth):
    sig = result["significant"]
    called_up = sig & (result["median_lfc"] > 0)
    called_down = sig & (result["median_lfc"] < 0)
    true_up, true_down = truth > 0.3, truth < -0.3
    return {
        "called": int(sig.sum()),
        "up": int(called_up.sum()),
        "down": int(called_down.sum()),
        "true positives": int((sig & (true_up | true_down)).sum()),
        "false positives": int((sig & ~(true_up | true_down)).sum()),
        "recall %": 100 * (sig & (true_up | true_down)).sum() / max((true_up | true_down).sum(), 1),
        "bias (median LFC of null genes)": float(np.median(result["median_lfc"][~(true_up | true_down)])),
    }


def main():
    control, treated, truth = make_sample()
    print(f"top-50 share of the library — control {np.median(top_gene_share(control)):.1f}% "
          f"vs treated {np.median(top_gene_share(treated)):.1f}%\n")

    variants = {
        "reference gene": paired_log2fc(treated, control, normalize="cp10k",
                                        reference_gene=REFERENCE_GENE),
        "median-of-ratios": paired_log2fc(treated, control, normalize="median-ratio"),
    }
    results = {}
    for name, lfc in variants.items():
        results[name] = paired_test(lfc)
        print(f"── normalised on the {name} ──")
        for k, v in score(results[name], truth).items():
            print(f"     {k:34s} {v:>8.1f}" if isinstance(v, float) else f"     {k:34s} {v:>8}")
        print()

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from gallery_style import CAT, axis_label, use_gallery_style, zero_line
    except ImportError:                                     # pragma: no cover
        print("matplotlib / gallery_style not installed — skipping the figure")
        return
    use_gallery_style()

    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2), sharex=True, sharey=True)
    for ax, (name, res) in zip(axes, results.items()):
        null = np.abs(truth) <= 0.3
        zero_line(ax)
        ax.axline((0, 0), slope=1, color="0.85", lw=0.8, ls="--", zorder=0)
        ax.scatter(truth[null], res["median_lfc"][null], s=6, alpha=0.35,
                   color=CAT(1), label="no true change")
        ax.scatter(truth[~null], res["median_lfc"][~null], s=14, alpha=0.85,
                   color=CAT(0), label="true change")
        s = score(res, truth)
        ax.set_title(f"normalised on the {name}\n"
                     f"{s['up']} up / {s['down']} down · "
                     f"{s['false positives']} false · bias {s['bias (median LFC of null genes)']:+.2f}",
                     fontsize=10)
        ax.set_xlabel(axis_label("planted fold change", "log2"))
    axes[0].set_ylabel(axis_label("estimated fold change", "log2"))
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    out = Path(__file__).resolve().parents[1] / "figures" / "before_after.png"
    fig.savefig(out, dpi=150)
    print(f"figure → {out}")


if __name__ == "__main__":
    main()
