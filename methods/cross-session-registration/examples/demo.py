"""Before/after: xy-only vs full 3-D registration of the same FOV across two days.

Same axon arbor, same boutons, but day 2 is displaced in x, y AND z (and brighter, with its
own noise). A 2-D registration on the mean image recovers x, y but leaves the z-offset — so
the same boutons don't line up and don't match. A 3-D vesselness registration recovers all
three axes and the boutons snap back onto each other.

Figure: an XZ view (z vertical, x horizontal) of the reference arbor, with reference boutons
(circles) and the day-2 boutons brought back by each registration (crosses). Left they sit a
few planes off in z; right they land on the circles.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, use_gallery_style
from make_sample import make_pair
from xsession import register_2d, register_3d, match_boutons, FOVShift


def _xz(stack):
    """XZ max-projection (max over y) → image (z, x)."""
    return stack.max(axis=1)


def main():
    use_gallery_style()
    s = make_pair(true_shift=(3, -6, 5))
    ref, mov = s["ref"], s["mov"]
    ref_c, mov_c = s["ref_cents"], s["mov_cents"]
    N = len(ref_c)

    # 2-D registration on the z-mean image (no z) vs full 3-D registration
    dx2, dy2, _ = register_2d(ref.mean(0), mov.mean(0))
    shift2d = FOVShift(dx=dx2, dy=dy2, dz_planes=0.0)
    shift3d = register_3d(ref, mov)

    m2 = match_boutons(ref_c, mov_c, shift2d, radius_px=4.0, z_radius_planes=1.0)
    m3 = match_boutons(ref_c, mov_c, shift3d, radius_px=4.0, z_radius_planes=1.0)

    bg = _xz(ref)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), constrained_layout=True)
    for ax, shift, matched, title in (
        (axes[0], shift2d, m2, "xy-only registration (mean image)"),
        (axes[1], shift3d, m3, "3-D vesselness registration"),
    ):
        ax.imshow(bg, cmap="Greys", origin="lower", aspect="auto",
                  vmin=np.percentile(bg, 40), vmax=np.percentile(bg, 99.5))
        # day-2 boutons brought back to the reference frame: mov − shift (SUBTRACT convention)
        back = mov_c - np.array([shift.dx, shift.dy, shift.dz_planes])
        ax.scatter(ref_c[:, 0], ref_c[:, 2], s=70, facecolors="none",
                   edgecolors=CAT(0), linewidths=1.6, label="day-1 boutons")
        ax.scatter(back[:, 0], back[:, 2], s=42, marker="x",
                   color=CAT(1), linewidths=1.6, label="day-2, re-registered")
        ax.set_title(f"{title}\n{len(matched)}/{N} boutons matched", fontsize=11)
        ax.set_xlabel("x (px)"); ax.set_ylabel("z (plane)")
        ax.set_ylim(0, ref.shape[0] - 1)
    axes[0].legend(loc="upper right", fontsize=8, framealpha=0.9)
    fig.suptitle("Same field of view across days: the z-offset xy-registration leaves behind",
                 fontsize=12)

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    print(f"true shift (dx,dy,dz) = {s['true']}")
    print(f"3-D recovered = dx {shift3d.dx:.2f}, dy {shift3d.dy:.2f}, dz {shift3d.dz_planes:.2f} "
          f"(peak {shift3d.xy_peak_corr:.2f})")
    print(f"boutons matched — xy-only: {len(m2)}/{N}   3-D: {len(m3)}/{N}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
