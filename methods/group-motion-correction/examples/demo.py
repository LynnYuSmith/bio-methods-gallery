"""Group-correct the sample TIFFs, write TIFF + HDF5, and draw a before/after figure."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile

from gallery_style import use_gallery_style, axis_label
from groupmc import correct_tiffs
from make_sample import make_sample


def main() -> None:
    use_gallery_style()
    here = Path(__file__).resolve().parent
    raw = make_sample(here / "raw")
    result = correct_tiffs(raw, here / "out")
    print("wrote HDF5:", result["hdf5"])

    # before: mean of each raw recording drifts apart. after: they align.
    raw_means = [np.asarray(tifffile.imread(p)).mean(0) for p in raw]
    reg_means = [np.asarray(tifffile.imread(t)).mean(0) for t in result["tiffs"]]
    fig, ax = plt.subplots(2, len(raw), figsize=(2.2 * len(raw), 4.6))
    for i, (rm, gm) in enumerate(zip(raw_means, reg_means)):
        ax[0, i].imshow(rm); ax[0, i].set_title(f"raw {i}"); ax[0, i].axis("off")
        ax[1, i].imshow(gm); ax[1, i].set_title(f"registered {i}"); ax[1, i].axis("off")
    ax[0, 0].set_ylabel("before"); ax[1, 0].set_ylabel("after")
    fig.suptitle("group motion correction: shared reference aligns the recordings", fontsize=10)
    fig.tight_layout()
    out = here.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    main()
