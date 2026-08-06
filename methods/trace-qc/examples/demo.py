"""Two QC gates on the two representations of a calcium trace.

Left: SNR on the ΔF/F trace (baseline removed) — clean vs noisy. Right: photobleaching on the
raw fluorescence (before ΔF/F, where the decay lives) — stable vs bleached, with the fitted
exponential drawn where the fit is trustworthy (high r²).
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from gallery_style import CAT, use_gallery_style
from make_sample import make_traces
from traceqc import photobleaching, snr


def main():
    use_gallery_style()
    s = make_traces(seed=0)
    fps = s["fps"]
    t = np.arange(len(s["clean"])) / fps

    fig, axes = plt.subplots(2, 2, figsize=(11, 6), sharex=True, constrained_layout=True)

    # --- left column: SNR on ΔF/F ---
    for row, name in enumerate(("clean", "noisy")):
        ax = axes[row, 0]
        q = snr(s[name], fs=fps)
        ax.plot(t, s[name], color=CAT(row), lw=0.6)
        ax.set_title(f"ΔF/F · {name}   —   SNR {q['snr_peak']:.1f}, grade {q['grade']}",
                     fontsize=10, loc="left")
        ax.set_ylabel("ΔF/F")

    # --- right column: photobleaching on raw F ---
    for row, name in enumerate(("raw_stable", "raw_bleached")):
        ax = axes[row, 1]
        tr = s[name]
        b = photobleaching(tr, fs=fps)
        ax.plot(t, tr, color=CAT(row + 2), lw=0.6)
        trustworthy = b["r_squared"] is not None and np.isfinite(b["r_squared"]) and b["r_squared"] > 0.5
        if trustworthy:
            fit = b["amplitude"] * np.exp(-t / b["tau"]) + b["offset"]
            ax.plot(t, fit, color="k", lw=1.4, ls="--", label="exp fit")
            msg = f"{b['decay_rate']:.0f}%/min  (r²={b['r_squared']:.2f})"
            ax.legend(loc="upper right", fontsize=8)
        else:
            msg = f"no real decay (r²={b['r_squared']:.2f})"
        ax.set_title(f"raw F · {name.replace('raw_', '')}   —   photobleaching: {msg}",
                     fontsize=10, loc="left")
        ax.set_ylabel("raw F")

    for ax in axes[-1]:
        ax.set_xlabel("time (s)")
    fig.suptitle("Per-trace QC: SNR (on ΔF/F) and photobleaching (on raw F) are separate gates",
                 fontsize=12)

    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=130)
    for name in ("clean", "noisy"):
        q = snr(s[name], fs=fps); print(f"SNR  {name:12s} peak {q['snr_peak']:5.2f} grade {q['grade']}")
    for name in ("raw_stable", "raw_bleached"):
        b = photobleaching(s[name], fs=fps)
        print(f"bleach {name:12s} {b['decay_rate']:.1f}%/min r²={b['r_squared']:.2f}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
