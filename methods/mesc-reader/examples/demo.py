"""Write a synthetic .mesc, read it, and show the per-channel display conversion in action.

Each channel's stored counts sit on a PMT **pedestal** (offset −786 green, −1170 red). The native
MESc reader subtracts it; so does this, by default, with a loud warning. The figure shows, per
channel: the stored frame and the converted frame (each on its own scale, so the signal stays
visible), and a histogram of pixel values — where the whole distribution slides left off the
pedestal and the background lands at **true zero**. That baseline-at-zero is the point: it's what
a collaborator sees in MESc, and what ΔF/F needs.
"""
import tempfile
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, SEQ, use_gallery_style
from make_sample import write_synthetic_mesc
from mescreader import list_units, read_frames


def main():
    use_gallery_style()
    d = Path(tempfile.mkdtemp())
    mesc = d / "synthetic.mesc"
    write_synthetic_mesc(mesc, n_units=1, frames=20, height=32, width=40, n_channels=2)
    units = list_units(mesc)

    for u in units:
        for ch, (s, o) in u["conversion"].items():
            print(f"{u['path']}/{ch}: conversion physical = stored*{s:g} + ({o:+g})")

    upath, frame = "MSession_0/MUnit_0", 8
    stored_c, applied_c = "#9aa0a8", CAT(0)
    fig, axes = plt.subplots(2, 2, figsize=(9.8, 6.4), constrained_layout=True,
                             gridspec_kw={"width_ratios": [1, 1.7]})

    for row, (ch, label) in enumerate((("Channel_0", "green"), ("Channel_1", "red"))):
        raw_stack = read_frames(mesc, upath, ch, apply_conversion=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            conv_stack = read_frames(mesc, upath, ch)              # default: applies + warns
        off = u["conversion"][ch][1]

        # one frame for context (a real recording, not the point — the histogram is)
        ax0 = axes[row, 0]
        ax0.imshow(raw_stack[frame], cmap=SEQ)
        ax0.set_title(f"{ch} ({label}) — a frame", fontsize=10)
        ax0.set_xticks([]); ax0.set_yticks([])

        # the story: the whole pixel distribution slides off the pedestal; background → 0
        axh = axes[row, 1]
        bins = np.linspace(-100, int(raw_stack.max()) + 50, 90)
        axh.hist(raw_stack.ravel(), bins=bins, color=stored_c, label="stored (on the pedestal)")
        axh.hist(conv_stack.ravel(), bins=bins, color=applied_c, label="converted (baseline 0)")
        axh.axvline(0, color="#444", lw=1.2, ls="--")
        ymax = axh.get_ylim()[1]
        axh.annotate("", xy=(0, ymax * 0.30), xytext=(-off, ymax * 0.30),
                     arrowprops=dict(arrowstyle="->", color="#555", lw=1.3))
        axh.text(-off / 2, ymax * 0.42, f"−{abs(off):g}", ha="center", fontsize=9, color="#555")
        axh.set_yscale("log")
        axh.set_xlabel("pixel value (counts)", fontsize=9)
        axh.set_ylabel("pixels (log)", fontsize=9)
        if row == 0:
            axh.legend(fontsize=8, frameon=False, loc="upper right")
        axh.set_title(f"pixel values: the {abs(off):g}-count pedestal is removed", fontsize=10)

        print(f"  {ch}: warning fired = {len(w) > 0}; "
              f"stored mean {raw_stack.mean():.0f} → converted {conv_stack.mean():.0f}")

    fig.suptitle("mesc-reader — the PMT pedestal is removed by default (loudly), baseline → 0",
                 fontsize=12)
    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
