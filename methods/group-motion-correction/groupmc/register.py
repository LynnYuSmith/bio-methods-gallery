"""Group motion correction: register several recordings of one field of view to a shared reference.

The usual pipeline motion-corrects each recording on its own, and each pass picks its own reference
frame. Across recordings the references differ, so the same physical cell or bouton lands on slightly
different pixels, and an ROI drawn once no longer fits the others.

Here every recording is registered to ONE shared reference, taken from the first recording. So one
ROI, drawn once, is the same physical structure in every recording. The workflow is the contribution:

    1. Build the reference from the first recording (its mean image).
    2. Register every frame of every recording to that one reference by whole-frame translation
       (phase correlation), the same rigid shift a per-recording pass uses.

The registration itself is standard (`skimage.registration.phase_cross_correlation`); the point is
that the reference is shared, so the outputs are directly comparable.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy.ndimage import shift as nd_shift
from skimage.registration import phase_cross_correlation


def reference_from(stack: np.ndarray) -> np.ndarray:
    """The shared reference: the mean image of a recording (frames, y, x)."""
    return stack.mean(axis=0)


def _register_frame(frame: np.ndarray, ref: np.ndarray):
    """Shift one frame onto `ref` by phase correlation. Returns (registered_frame, (dy, dx))."""
    (dy, dx), _, _ = phase_cross_correlation(ref, frame, upsample_factor=10)
    reg = nd_shift(frame, (dy, dx), order=1, mode="nearest")
    return reg, (float(dy), float(dx))


def register_to_reference(stack: np.ndarray, ref: np.ndarray):
    """Register every frame of `stack` to `ref`. Returns (registered_stack, shifts (n, 2) as dy,dx)."""
    out = np.empty_like(stack)
    shifts = np.empty((stack.shape[0], 2), float)
    for i in range(stack.shape[0]):
        out[i], shifts[i] = _register_frame(stack[i], ref)
    return out, shifts


def group_motion_correct(stacks: Sequence[np.ndarray]):
    """Register a group of recordings of one FOV to a shared reference (the first recording's mean).

    Parameters
    ----------
    stacks
        One array per recording, each (frames, y, x), all the same y, x.

    Returns
    -------
    registered : list of arrays
        Each recording registered to the shared reference.
    ref : array
        The shared reference image (y, x).
    shifts : list of arrays
        Per-recording per-frame shifts (n_frames, 2) as (dy, dx). These are the motion-correction
        evidence: keep them, they say how much each frame moved.
    """
    if not stacks:
        raise ValueError("no recordings given")
    shapes = {s.shape[1:] for s in stacks}
    if len(shapes) != 1:
        raise ValueError(f"recordings differ in frame size: {shapes}")
    ref = reference_from(stacks[0])
    registered, shifts = [], []
    for st in stacks:
        reg, sh = register_to_reference(st, ref)
        registered.append(reg)
        shifts.append(sh)
    return registered, ref, shifts
