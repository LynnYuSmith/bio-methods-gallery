"""Show the contribution: an unclipped rolling MEDIAN baseline (ΔF/F symmetric around zero)
vs a rolling LOWER-ENVELOPE baseline (ΔF/F biased above zero)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, axis_label, use_gallery_style, zero_line
from make_sample import make_trace
from dffbaseline import dff, lower_envelope_baseline, median_baseline


def main() -> None:
    use_gallery_style()
    s = make_trace()
    f, fps = s["f"], s["fps"]
    t = np.arange(len(f)) / fps

    f0_med = median_baseline(f, fps=fps, win_s=20.0)
    f0_env = lower_envelope_baseline(f, fps=fps, win_s=20.0, q=0.1)
    dff_med, dff_env = dff(f, f0_med), dff(f, f0_env)
    quiet = s["quiet"]

    fig, ax = plt.subplots(2, 1, figsize=(8.4, 4.8), sharex=True)
    ax[0].plot(t, f, color="#bdbdbd", lw=0.8, label="fluorescence F")
    ax[0].plot(t, f0_med, color=CAT(1), lw=1.5, label="median baseline (q=0.5, unclipped)")
    ax[0].plot(t, f0_env, color=CAT(4), lw=1.5, label="lower-envelope (q=0.1, clipped)")
    ax[0].set_ylabel(axis_label("F", "a.u."))
    ax[0].legend(fontsize=7, loc="upper right", framealpha=0.9)

    ax[1].plot(t, dff_env, color=CAT(4), lw=0.8, label="ΔF/F, lower-envelope (biased up)")
    ax[1].plot(t, dff_med, color=CAT(1), lw=0.8, label="ΔF/F, median (centred on 0)")
    zero_line(ax[1])
    ax[1].set_xlabel(axis_label("time", "s"))
    ax[1].set_ylabel(axis_label("ΔF/F", "a.u."))
    ax[1].legend(fontsize=7, loc="upper right", framealpha=0.9)

    fig.suptitle("dF/F baseline: an unclipped median sits in the noise (ΔF/F centred on 0); "
                 "a lower-envelope sits below it (ΔF/F biased up)", fontsize=9)
    fig.tight_layout()

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)

    print(f"quiet-region median ΔF/F:  median baseline {np.median(dff_med[quiet]):+.3f}  |  "
          f"lower-envelope {np.median(dff_env[quiet]):+.3f}")


if __name__ == "__main__":
    main()
