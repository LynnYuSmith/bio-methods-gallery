"""Show the contribution: mean-image blob detection vs activity-based, data-driven-window detection."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import use_gallery_style
from boutons import detect_boutons, detect_blobs, activity_map
from make_sample import make_recording


def _circles(ax, blobs, color):
    for r, c, s in blobs:
        ax.add_patch(plt.Circle((c, r), s * np.sqrt(2), fill=False, color=color, lw=1.0))


def main() -> None:
    use_gallery_style()
    stack, ps, _ = make_recording()
    mean_img = stack.mean(0)
    act = activity_map(stack)

    baseline = detect_blobs(mean_img)                 # naive: blobs on the mean image
    boutons, all_act_blobs, window = detect_boutons(stack, ps)

    fig, ax = plt.subplots(1, 3, figsize=(10, 3.4))
    ax[0].imshow(mean_img, cmap="cmc.grayC"); ax[0].set_title(f"mean image + blobs (n={len(baseline)})")
    _circles(ax[0], baseline, "#9e7b8a")              # catches the static shaft too
    ax[1].imshow(act, cmap="cmc.grayC"); ax[1].set_title("activity map")
    ax[2].imshow(act, cmap="cmc.grayC"); ax[2].set_title(f"boutons (n={len(boutons)})")
    _circles(ax[2], boutons, "#6b7f9e")               # shaft is flat in time -> not detected
    for a in ax:
        a.set_xticks([]); a.set_yticks([]); a.grid(False)
    fig.suptitle(f"bouton detection: activity, not brightness; size window {window[0]:.1f}–{window[1]:.1f} µm "
                 f"from the active regions", fontsize=10)
    fig.tight_layout()
    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"mean-image blobs {len(baseline)} (includes the shaft); "
          f"activity boutons {len(boutons)}; window {window[0]:.2f}-{window[1]:.2f} um")


if __name__ == "__main__":
    main()
