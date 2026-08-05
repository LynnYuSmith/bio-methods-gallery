"""Show the contribution: a per-frame pupil detector alone vs the same detector run
through the tracking tool (temporal consistency + gap interpolation)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, axis_label, use_gallery_style
from make_sample import make_eye_video
from pupiltrack import detect_pupil, track_pupil


def main() -> None:
    use_gallery_style()
    frames, truth = make_eye_video()
    gt = truth["radius"]
    t = np.arange(len(frames))

    naive = np.array([(detect_pupil(f) or (np.nan, np.nan, np.nan))[2] for f in frames])
    tracked = track_pupil(frames)["radius"]

    fig, ax = plt.subplots(1, 1, figsize=(8.2, 3.4))
    for b in truth["blinks"]:
        ax.axvline(b, color="#e6e6e6", lw=3, zorder=0)
    ax.plot(t, gt, color="#9a9a9a", lw=2.2, label="true pupil radius")
    ax.plot(t, naive, color=CAT(4), lw=1.0, marker=".", ms=3, label="per-frame detector (naive)")
    ax.plot(t, tracked, color=CAT(1), lw=1.7, label="tracking tool")
    ax.set_xlabel(axis_label("frame"))
    ax.set_ylabel(axis_label("pupil radius", "px"))
    ax.set_title("pupil tracking: temporal consistency recovers what the per-frame detector loses",
                 fontsize=10)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.9)
    fig.tight_layout()

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)

    err_naive = float(np.nanmean(np.abs(naive - gt)))
    err_tracked = float(np.nanmean(np.abs(tracked - gt)))
    n_drop = int(np.isnan(naive).sum())
    print(f"mean|err|  naive {err_naive:.2f} px ({n_drop} dropped frames)  |  "
          f"tracked {err_tracked:.2f} px ({int(np.isnan(tracked).sum())} dropped)")


if __name__ == "__main__":
    main()
