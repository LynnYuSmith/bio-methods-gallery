"""Per-frame pupil measurement by fitting its BORDER, for bright-pupil (coaxial IR) video.

Under coaxial infrared illumination the pupil retro-reflects and becomes the brightest
structure in the eye: a saturated plateau with a sharp fall into the darker iris. That
geometry invites a very different measurement from the usual "threshold and take the blob".

**Why not a blob.** A threshold answers *how many pixels are bright*, and lid glare is also
bright. Where glare touches the pupil the two merge into one region and the blob's equivalent
radius grows smoothly, so the failure looks exactly like a dilation and cannot be detected
downstream. The bright region's AREA is therefore the wrong observable.

**What is measured instead.** The border. Rays are cast outward from an anchored centre; on
each ray the crossing of the half-drop level between the plateau and the iris trough is found
to sub-pixel precision; a least-squares circle is fitted through the confirmed crossings. Three
things make that robust:

* a ray only counts if its darkness **holds** for a few micrometres past the crossing. A ray
  grazing an eyelash or the rim of a glare band dips below the level and climbs straight back
  out — the border does not.
* a crossing whose hold cannot be verified **inside the given rectangle** is discarded. A ray
  aimed at a dark corner of a tight eye window leaves the image a sample or two after it drops,
  and forty-eight such rays fit a circle the size of the window to a fraction of a pixel — a
  clean fit to nothing. This is the single most dangerous failure of the method and it is
  cheap to close.
* the fit is judged by its **residual and visible arc**, not by how many points it has. A real
  border gives a sharp contour from few points; an over-reading fit scatters. Frame counts and
  residuals correlate only weakly, so the residual is the discriminator.

A frame whose fit fails those guards is REFUSED rather than guessed. A refusal is information:
a blink has no pupil to measure, and reporting a number for it corrupts every average
downstream. The trace that comes out therefore has honest gaps, which ``track.py`` fills only
where interpolation is defensible.

**Calibration.** The half-drop border sits slightly inside the disc a human outlines, by a
constant that depends on the optics rather than on the pupil: an ADDITIVE offset, not a scale
factor. Measure it once per rig against a handful of hand-drawn references and add it; do not
tune the level to make the constant small, which improves the constant and worsens the
agreement.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

# --- the measured defaults ----------------------------------------------------------------
RAYS = 48               # 72 buys nothing over 48; below ~24 the arc guard starts to bite
SLOPE_FRAC = 0.4        # the level: plateau minus this fraction of the plateau-to-trough drop
HOLD_FRAC = 0.05        # how much the trace may climb back and still count as "held"
TAIL_PX = 3.0           # how far past the crossing the darkness has to hold
MAX_RESIDUAL = 1.0      # px, median distance of the confirmed points from the fitted circle
MIN_ARC = 110.0         # degrees of border that must be visible for a radius to be determined
MIN_CONTRAST = 15.0     # plateau minus trough, in grey levels; below this there is no border
SAT_FRAC = 0.92         # a pixel this bright, relative to the frame's max, is "plateau"
EDGE_OFFSET = 0.0       # rig calibration, added to the radius; measure it, do not guess it


def _prep(frame) -> np.ndarray:
    f = np.asarray(frame, dtype=float)
    if f.ndim != 2:
        raise ValueError("frame must be 2-D (an eye-ROI stack is (n, H, W))")
    return gaussian_filter(f, 1.0)


def pupil_centre(frame, anchor=None, search_px: float = 20.0):
    """Centre of the bright plateau: ``(cy, cx)`` or ``None``.

    With an ``anchor`` (the previous frame's centre) the search is restricted to a disc of
    ``search_px`` around it, which is what stops the tracker walking off onto a brighter
    reflection elsewhere in the window. Without one, the densest bright cell of the frame is
    taken — good enough to start, and the temporal layer corrects it from the second frame on.
    """
    g = _prep(frame)
    hi = g.max()
    if hi <= 0:
        return None
    mask = g >= SAT_FRAC * hi
    if anchor is not None:
        yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
        near = (yy - anchor[0]) ** 2 + (xx - anchor[1]) ** 2 <= search_px ** 2
        mask = mask & near
        if not mask.any():                      # the anchor may be stale after a long blink
            mask = g >= SAT_FRAC * hi
    if not mask.any():
        return None
    # the centre of the LARGEST bright neighbourhood, not of all bright pixels: a glare band
    # elsewhere in the window would otherwise drag the mean towards itself
    dens = uniform_filter(mask.astype(float), size=7)
    cy, cx = np.unravel_index(int(np.argmax(dens)), dens.shape)
    win = 9
    y0, y1 = max(0, cy - win), min(g.shape[0], cy + win + 1)
    x0, x1 = max(0, cx - win), min(g.shape[1], cx + win + 1)
    sub = mask[y0:y1, x0:x1]
    if sub.any():
        ys, xs = np.nonzero(sub)
        cy, cx = y0 + ys.mean(), x0 + xs.mean()
    return float(cy), float(cx)


def _levels(g: np.ndarray, cy: float, cx: float):
    """(plateau, trough, level) from the radial brightness profile, or ``None``.

    The plateau is the pupil's own brightness, the trough the iris behind its border. Both are
    read from annuli around the centre rather than from the whole frame, so a bright structure
    at the edge of the window cannot set the scale.
    """
    yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
    rr = np.hypot(xx - cx, yy - cy)
    ks, vs = [], []
    for k in np.arange(0, min(g.shape) / 2, 1.0):
        m = (rr >= k) & (rr < k + 1)
        if m.sum() >= 4:
            ks.append(k + 0.5)
            vs.append(float(g[m].mean()))
    if len(ks) < 8:
        return None
    vs = np.asarray(vs)
    plateau = float(np.max(vs[:max(3, len(vs) // 6)]))     # the innermost annuli
    trough = float(np.min(vs))
    if plateau - trough < MIN_CONTRAST:
        return None
    return plateau, trough, plateau - SLOPE_FRAC * (plateau - trough)


def _ray_edge(g: np.ndarray, cy: float, cx: float, ca: float, sa: float,
              level: float, rmax: float, hold: float):
    """Where one ray crosses ``level``, and whether that fall held. ``None`` if it did not."""
    r = np.arange(int(rmax / 0.5) + 1) * 0.5
    xs, ys = cx + ca * r, cy + sa * r
    keep = (xs >= 0) & (ys >= 0) & (xs < g.shape[1] - 1) & (ys < g.shape[0] - 1)
    if keep.sum() < 10:
        return None
    r, xs, ys = r[keep], xs[keep], ys[keep]
    x0, y0 = xs.astype(int), ys.astype(int)
    fx, fy = xs - x0, ys - y0
    v = ((g[y0, x0] * (1 - fx) + g[y0, x0 + 1] * fx) * (1 - fy)
         + (g[y0 + 1, x0] * (1 - fx) + g[y0 + 1, x0 + 1] * fx) * fy)
    below = np.nonzero(v <= level)[0]
    below = below[below > 0]
    if not len(below):
        return None
    i = int(below[0])
    n_tail = max(2, int(TAIL_PX / 0.5) + 1)
    if i + n_tail > len(v):          # the hold cannot be verified inside the given rectangle
        return None
    if v[i:i + n_tail].max() > level + hold:      # it dipped and climbed back out
        return None
    edge = r[i - 1] + (v[i - 1] - level) / (v[i - 1] - v[i] + 1e-9) * (r[i] - r[i - 1])
    return float(edge)


def fit_circle(points: np.ndarray):
    """Least-squares circle through ``(y, x)`` points: ``(cy, cx, radius, residual)``.

    The algebraic (Kåsa) fit, which is linear and needs no starting guess. ``residual`` is the
    median distance of the points from the fitted circle — the number that decides whether the
    points were a border at all.
    """
    if len(points) < 3:
        return None
    y, x = points[:, 0].astype(float), points[:, 1].astype(float)
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x ** 2 + y ** 2
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:               # pragma: no cover
        return None
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    rad2 = sol[2] + cx ** 2 + cy ** 2
    if rad2 <= 0:
        return None
    radius = float(np.sqrt(rad2))
    resid = float(np.median(np.abs(np.hypot(x - cx, y - cy) - radius)))
    return float(cy), float(cx), radius, resid


def detect_border(frame, anchor=None, search_px: float = 20.0, rays: int = RAYS,
                  edge_offset: float = EDGE_OFFSET):
    """Measure one frame's pupil border.

    Returns a dict with ``cy``, ``cx``, ``radius``, ``residual``, ``arc_deg``, ``contrast``,
    ``n_rays`` and ``status``. ``status`` is ``"ok"`` or the reason the frame was refused:
    ``"no_centre"``, ``"no_contrast"``, ``"few_rays"``, ``"short_arc"`` or ``"poor_fit"``.
    """
    out = dict(cy=np.nan, cx=np.nan, radius=np.nan, residual=np.nan, arc_deg=np.nan,
               contrast=np.nan, n_rays=0, status="no_centre")
    g = _prep(frame)
    c = pupil_centre(g, anchor=anchor, search_px=search_px)
    if c is None:
        return out
    cy, cx = c
    lv = _levels(g, cy, cx)
    if lv is None:
        out["status"] = "no_contrast"
        return out
    plateau, trough, level = lv
    out["contrast"] = plateau - trough
    hold = HOLD_FRAC * (plateau - trough)
    rmax = min(g.shape) / 2.0
    angles = np.linspace(0, 2 * np.pi, rays, endpoint=False)
    pts, kept_angles = [], []
    for a in angles:
        e = _ray_edge(g, cy, cx, np.cos(a), np.sin(a), level, rmax, hold)
        if e is not None:
            pts.append((cy + np.sin(a) * e, cx + np.cos(a) * e))
            kept_angles.append(a)
    out["n_rays"] = len(pts)
    if len(pts) < 5:
        out["status"] = "few_rays"
        return out
    # how far round the circle the confirmed points reach: a short arc of a small circle looks
    # like a short arc of a large one however well the points sit on it
    ka = np.sort(np.asarray(kept_angles))
    gaps = np.diff(np.concatenate([ka, ka[:1] + 2 * np.pi]))
    arc = float(np.degrees(2 * np.pi - gaps.max()))
    out["arc_deg"] = arc
    if arc < MIN_ARC:
        out["status"] = "short_arc"
        return out
    fit = fit_circle(np.asarray(pts))
    if fit is None:
        out["status"] = "poor_fit"
        return out
    fcy, fcx, radius, resid = fit
    out.update(cy=fcy, cx=fcx, radius=radius + edge_offset, residual=resid)
    out["status"] = "ok" if resid <= MAX_RESIDUAL else "poor_fit"
    if out["status"] != "ok":
        out["radius"] = np.nan
    return out


def detect_pupil(frame, **kwargs):
    """``(cy, cx, radius)`` for one frame, or ``None`` if the frame was refused."""
    r = detect_border(frame, **kwargs)
    if r["status"] != "ok":
        return None
    return r["cy"], r["cx"], r["radius"]


def detect_brightest_blob(frame, sat_frac: float = SAT_FRAC):
    """The naive reading, kept only so the demo can show what it costs.

    Threshold the bright pixels and report the equivalent radius of the largest bright region.
    This is what merges the pupil with lid glare and calls the result a dilation.
    """
    from scipy import ndimage
    g = _prep(frame)
    hi = g.max()
    if hi <= 0:
        return None
    mask = g >= sat_frac * hi
    if not mask.any():
        return None
    labels, n = ndimage.label(mask)
    if n == 0:
        return None
    areas = ndimage.sum(np.ones_like(labels, dtype=float), labels, index=np.arange(1, n + 1))
    k = int(np.argmax(areas)) + 1
    cy, cx = ndimage.center_of_mass(mask, labels, k)
    return float(cy), float(cx), float(np.sqrt(float(areas[k - 1]) / np.pi))
