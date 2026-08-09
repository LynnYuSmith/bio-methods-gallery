"""Group motion correction on a synthetic train of .mesc repeats — the shared-grid payoff.

Three repeats of one field of view, each with its own within-repeat drift *and* a per-repeat
baseline offset (the FOV sat a little differently each run). We build ONE shared reference from
repeat 0 (the anchor) and hand it to the whole train. The figure shows the point of the group
method: measured against that shared reference, the raw repeats sit off the grid (later repeats
worst — their baseline offset), and after group correction every repeat lands on the same grid.
"""
import tempfile
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, SEQ, use_gallery_style
from make_sample import write_synthetic_train
from mescmc import build_group_reference, correct_train, estimate_shift, read_channel


def _disp_to_grid(mean_img, reference, offset):
    """How far a repeat's mean image sits from the shared grid (px)."""
    dy, dx = estimate_shift(reference, np.clip(mean_img + offset, 0, None))
    return float(np.hypot(dy, dx))


def main():
    use_gallery_style()
    d = Path(tempfile.mkdtemp())
    gt = write_synthetic_train(d / "raw", n_reps=3, frames=30, height=64, width=64, seed=2)
    train = [(p, "MSession_0/MUnit_0") for p in gt["paths"]]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reference = build_group_reference(train, warn=False)
        results = correct_train(train, reference, warn=False)

    n = len(train)
    raw_disp, corr_disp = [], []
    for (p, upath), res in zip(train, results):
        raw_mean = read_channel(p, upath, "Channel_0").astype(np.float32).mean(0)
        corr_mean = res["Channel_0"].astype(np.float32).mean(0)
        raw_disp.append(_disp_to_grid(raw_mean, reference, res["offset"]))
        corr_disp.append(_disp_to_grid(corr_mean, reference, res["offset"]))

    fig, axes = plt.subplots(2, 2, figsize=(9.6, 7.4), constrained_layout=True)

    # shared reference (the anchor, from repeat 0)
    ax = axes[0, 0]
    ax.imshow(reference, cmap=SEQ)
    ax.set_title("shared reference (from repeat 0 — the anchor)", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])

    # the hero: displacement of each repeat to the shared grid, raw vs group-corrected
    ax = axes[0, 1]
    x = np.arange(n)
    ax.bar(x - 0.18, raw_disp, 0.36, label="raw", color="#9aa0a8")
    ax.bar(x + 0.18, corr_disp, 0.36, label="group-corrected", color=CAT(0))
    ax.set_xticks(x); ax.set_xticklabels([f"repeat {i}" for i in range(n)])
    ax.set_ylabel("displacement to shared grid (px)", fontsize=9)
    ax.set_title("every repeat lands on one grid", fontsize=10)
    ax.legend(fontsize=8, frameon=False)

    # a worst-case repeat: raw mean (off-grid + motion-blurred) vs corrected (on-grid, sharp)
    worst = int(np.argmax(raw_disp))
    p, upath = train[worst]
    raw_mean = read_channel(p, upath, "Channel_0").astype(np.float32).mean(0)
    corr_mean = results[worst]["Channel_0"].astype(np.float32).mean(0)
    vmax = float(np.percentile(raw_mean, 99.5))
    for ax, img, ttl in ((axes[1, 0], raw_mean, f"repeat {worst} — raw mean (off-grid, blurred)"),
                         (axes[1, 1], corr_mean, f"repeat {worst} — corrected mean (on-grid, sharp)")):
        ax.imshow(img, cmap=SEQ, vmax=vmax)
        ax.set_title(ttl, fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])

    fig.suptitle("group motion correction — one shared reference registers the whole train of repeats",
                 fontsize=12)
    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"raw displacement to grid  : {[round(v,2) for v in raw_disp]} px")
    print(f"group-corrected to grid   : {[round(v,2) for v in corr_disp]} px")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
