"""Detect axonal boutons by their ACTIVITY, and let the active regions set the size window.

A bouton is a spot that fluctuates over time. So detection runs on an activity map (the temporal
variation of the recording), not on the mean image. A bright but static structure, an axon shaft
crossing the plane, is bright in the mean image yet flat in time, so it never appears on the
activity map and is not mistaken for a bouton.

The size window is not a hardcoded guess. It is read from the recording itself: the active regions
(what a functional segmenter such as Suite2p returns) have a size distribution, and the detection
bounds are taken from that distribution. So "how big is a bouton here" is answered by the data, at
whatever magnification, with a physiological range only as an outer sanity bound.

The workflow is the contribution: activity-based detection, plus a size window derived from the
recording's own active regions, rather than blob detection on a mean image with a fixed size filter.
"""
from __future__ import annotations

import numpy as np
from skimage.feature import blob_log
from skimage.measure import label, regionprops

# Outer physiological sanity bounds (microns). The working window is derived from the data and only
# clipped to this range, so a noisy recording cannot push the window somewhere unphysical.
SANITY_MIN_UM = 0.3
SANITY_MAX_UM = 4.0


def activity_map(stack: np.ndarray) -> np.ndarray:
    """The temporal standard deviation per pixel (frames, y, x) -> (y, x).

    High where the signal fluctuates over time (a firing bouton), low on a static structure. This
    is the functional signal a segmenter keys on, in one line.
    """
    return stack.astype(float).std(axis=0)


def active_regions(stack: np.ndarray, activity_percentile: float = 95.0):
    """Connected active regions and their equivalent diameters (in pixels).

    Threshold the activity map at a high percentile, label the connected components, and measure each
    one's size. These are the functionally active spots that define what a bouton looks like here.
    """
    act = activity_map(stack)
    thr = np.percentile(act, activity_percentile)
    mask = act > thr
    props = regionprops(label(mask))
    diams_px = np.array([p.equivalent_diameter for p in props])
    return act, mask, diams_px


def size_window_from_active(diams_px: np.ndarray, pixel_size_um: float, spread: float = 1.5):
    """A data-driven diameter window (microns) from the active regions' sizes.

    The window is the median active-region diameter divided and multiplied by `spread`, clipped to
    the physiological sanity range. With no active regions it falls back to the sanity bounds.
    """
    if diams_px.size == 0:
        return SANITY_MIN_UM, SANITY_MAX_UM
    med_um = float(np.median(diams_px)) * pixel_size_um
    lo = max(SANITY_MIN_UM, med_um / spread)
    hi = min(SANITY_MAX_UM, med_um * spread)
    return lo, hi


def detect_blobs(image: np.ndarray, min_sigma: float = 1.0, max_sigma: float = 8.0,
                 threshold: float = 0.05):
    """All Laplacian-of-Gaussian blobs in `image`. Returns (n, 3): row, col, sigma."""
    img = image.astype(float)
    rng = img.max() - img.min()
    if rng > 0:
        img = (img - img.min()) / rng
    return blob_log(img, min_sigma=min_sigma, max_sigma=max_sigma, num_sigma=10,
                    threshold=threshold)


def blob_diameter_um(blobs: np.ndarray, pixel_size_um: float) -> np.ndarray:
    """Blob diameter in microns. For a LoG blob the radius is sigma * sqrt(2)."""
    return 2 * blobs[:, 2] * np.sqrt(2) * pixel_size_um


def detect_boutons(stack: np.ndarray, pixel_size_um: float, spread: float = 1.5, **blob_kwargs):
    """Detect boutons from a recording: on the activity map, with a data-driven size window.

    Parameters
    ----------
    stack
        The recording, (frames, y, x).
    pixel_size_um
        Microns per pixel.
    spread
        Half-width of the data-driven size window around the median active-region diameter.

    Returns
    -------
    boutons : (n, 3) array
        Kept blobs (row, col, sigma), on the activity map, inside the data-driven size window.
    all_blobs : (m, 3) array
        Every blob on the activity map before the size window (for the before/after comparison).
    window_um : (float, float)
        The data-driven (min, max) diameter window that was used.
    """
    act, _, diams_px = active_regions(stack)
    lo, hi = size_window_from_active(diams_px, pixel_size_um, spread)
    all_blobs = detect_blobs(act, **blob_kwargs)
    if all_blobs.size == 0:
        return all_blobs, all_blobs, (lo, hi)
    d = blob_diameter_um(all_blobs, pixel_size_um)
    keep = (d >= lo) & (d <= hi)
    return all_blobs[keep], all_blobs, (lo, hi)
