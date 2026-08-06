"""Write a synthetic .mesc, read it, and show the per-channel display conversion in action.

Each channel's stored counts sit on a PMT offset (−786 green, −1170 red). The native MESc reader
subtracts it; so does this, by default, with a loud warning. The figure shows one raw frame and
the converted frame for each channel — the background drops toward zero, the signal stays.
"""
import tempfile
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import use_gallery_style
from make_sample import write_synthetic_mesc
from mescreader import list_units, read_frames


def main():
    use_gallery_style()
    d = Path(tempfile.mkdtemp())
    mesc = d / "synthetic.mesc"
    write_synthetic_mesc(mesc, n_units=1, frames=20, height=32, width=40, n_channels=2)

    for u in list_units(mesc):
        for ch, (s, o) in u["conversion"].items():
            print(f"{u['path']}/{ch}: conversion physical = stored*{s:g} + ({o:+g})")

    upath, frame = "MSession_0/MUnit_0", 8
    fig, axes = plt.subplots(2, 2, figsize=(8, 6.5), constrained_layout=True)
    for row, (ch, label) in enumerate((("Channel_0", "green"), ("Channel_1", "red"))):
        raw = read_frames(mesc, upath, ch, apply_conversion=False)[frame]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            conv = read_frames(mesc, upath, ch)[frame]           # default: applies + warns
        _, off = next(c for c in [u["conversion"][ch] for u in list_units(mesc)])
        for col, (img, ttl) in enumerate(((raw, f"{ch} ({label}) — stored"),
                                          (conv, f"→ conversion applied ({off:+g})"))):
            ax = axes[row, col]
            ax.imshow(img, cmap="Greys_r", vmin=0, vmax=float(raw.max()))
            ax.set_title(ttl, fontsize=10)
            ax.set_xticks([]); ax.set_yticks([])
        print(f"  {ch}: warning fired = {len(w) > 0}; "
              f"stored mean {raw.mean():.0f} → converted {conv.mean():.0f}")
    fig.suptitle("mesc-reader: the per-channel display conversion is applied by default (loudly)",
                 fontsize=12)

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
