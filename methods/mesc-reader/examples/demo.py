"""Write a synthetic .mesc, convert it both ways, and confirm the frames come out bit-identical.

A converter's whole job is to change nothing. The figure shows one raw frame straight from the
.mesc next to the same frame read back from the TIFF and from the HDF5 mirror — identical, by
construction — with the check that every pixel matches.
"""
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import use_gallery_style
from make_sample import write_synthetic_mesc
from mescreader import list_units, mesc_to_hdf5, mesc_to_tiff, read_frames


def main():
    use_gallery_style()
    d = Path(tempfile.mkdtemp())
    mesc = d / "synthetic.mesc"
    truth = write_synthetic_mesc(mesc, n_units=2, frames=20, height=32, width=40, n_channels=2)

    for u in list_units(mesc):
        print(f"{u['path']}  {u['frames']} frames  {u['height']}x{u['width']}  "
              f"{u['frame_rate_hz']:.1f} Hz  channels={u['channels']}")

    tiffs = mesc_to_tiff(mesc, d / "tiff")
    h5 = mesc_to_hdf5(mesc, d / "out.h5")

    import h5py
    import tifffile
    upath, ch, frame = "MSession_0/MUnit_0", "Channel_0", 8
    src = read_frames(mesc, upath, ch)[frame]
    tif = tifffile.imread(d / "tiff" / "MSession_0_MUnit_0_Channel_0.tif")[frame]
    with h5py.File(h5, "r") as f:
        hdf = f[f"{upath}/{ch}"][frame]

    ok_tif = np.array_equal(tif, src)
    ok_h5 = np.array_equal(hdf, src)
    print(f"TIFF bit-identical: {ok_tif}   HDF5 bit-identical: {ok_h5}")

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.6), constrained_layout=True)
    for ax, img, ttl in ((axes[0], src, ".mesc (raw)"),
                         (axes[1], tif, f"→ TIFF  ({'identical' if ok_tif else 'DIFF'})"),
                         (axes[2], hdf, f"→ HDF5  ({'identical' if ok_h5 else 'DIFF'})")):
        ax.imshow(img, cmap="Greys_r")
        ax.set_title(ttl, fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("mesc-reader: raw frames out, unchanged (no correction, no scaling)", fontsize=12)

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"wrote {len(tiffs)} TIFFs, 1 HDF5, and {out}")


if __name__ == "__main__":
    main()
