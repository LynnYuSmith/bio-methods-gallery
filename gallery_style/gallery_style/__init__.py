"""Shared plotting style for the gallery: a quiet, print-journal look.

White ground, black text, muted colours, thin lines. It reads like a figure from a 2010-era
methods paper, not a dashboard. The colour maps are Fabio Crameri's scientific set (perceptually
uniform, colour-blind-safe, greyscale-legible), which keeps the calm look honest rather than merely
desaturated. Every tile and notebook draws in this one style, so the series reads as one.

    from gallery_style import use_gallery_style, zero_line, SEQ, DIV, CAT
    use_gallery_style()                        # white ground, light-grey grid, black axes
    plt.imshow(m, cmap=SEQ)                     # sequential, muted grey ramp (grayC)
    plt.imshow(d, cmap=DIV, vmin=-1, vmax=1)    # diverging, soft blue-grey-brown (broc), zero-centred
    color = CAT(i)                              # categorical, muted (a few quiet hues)
    zero_line(ax)                               # darker-grey y=0 reference, behind the data

Reference: Crameri, F. (2023) Scientific colour maps v8.0. https://www.fabiocrameri.ch/colourmaps/
"""
from __future__ import annotations

# Sequential: a quiet grey ramp for magnitude (intensity, densities, heatmaps).
SEQ = "cmc.grayC"
# Diverging: a soft, low-saturation blue-grey-brown around zero (correlations, differences).
DIV = "cmc.broc"
# Light grey for the grid; a slightly darker grey for the zero reference line.
GRID = "#e6e6e6"
ZERO = "#9a9a9a"
# A muted categorical set: a handful of quiet hues that sit calmly on white.
_CAT_HEX = (
    "#3b3b3b",   # near-black grey
    "#6b7f9e",   # muted slate blue
    "#a08262",   # muted tan
    "#7a9471",   # muted sage
    "#9e7b8a",   # muted mauve
    "#5f8a8b",   # muted teal
)


def use_gallery_style() -> None:
    """Register the Crameri maps and set the quiet white-ground matplotlib defaults."""
    import cmcrameri  # noqa: F401  (import registers the cmc.* colormaps with matplotlib)
    import matplotlib as mpl

    mpl.rcParams.update({
        "image.cmap": SEQ,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "figure.dpi": 130,
        "savefig.bbox": "tight",
        "axes.edgecolor": "black",
        "axes.labelcolor": "black",
        "text.color": "black",
        "xtick.color": "black",
        "ytick.color": "black",
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.2,
        "axes.grid": True,
        "grid.color": GRID,           # light grey grid, always on
        "grid.linewidth": 0.6,
        "grid.alpha": 1.0,
        "axes.axisbelow": True,       # grid sits behind the data
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.prop_cycle": mpl.cycler(color=list(_CAT_HEX)),
        "font.size": 9,
        "font.family": "sans-serif",
    })


def zero_line(ax, axis: str = "y") -> None:
    """Draw the zero reference in a slightly darker grey than the grid, behind the data.

    axis="y" draws a horizontal line at y=0 (the usual case for traces); "x" a vertical one at
    x=0; "both" draws both.
    """
    kw = dict(color=ZERO, linewidth=0.9, zorder=0.5)
    if axis in ("y", "both"):
        ax.axhline(0, **kw)
    if axis in ("x", "both"):
        ax.axvline(0, **kw)


def axis_label(name: str, unit: str | None = None) -> str:
    """Format an axis label the journal way: the quantity, a comma, then the unit.

        axis_label("time", "s")      -> "time, s"
        axis_label("ΔF/F", "a.u.")   -> "ΔF/F, a.u."
        axis_label("ROI")            -> "ROI"        (dimensionless quantities carry no unit)

    Use it for every axis, so units read consistently across the gallery ("time, s", never
    "time (s)").
    """
    return f"{name}, {unit}" if unit else name


def CAT(i: int) -> str:
    """A muted categorical colour by index (cycles through a few quiet hues)."""
    return _CAT_HEX[i % len(_CAT_HEX)]
