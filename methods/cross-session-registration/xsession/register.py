"""Tile-facing API — thin wrappers over the REAL pipeline cross-session registration.

The maths lives in ``_synced.py`` (copied verbatim from the lab pipeline by ``_sync/sync.py``
and de-identified): 2-D and full 3-D FOV registration, plus 3-D bouton matching. These
wrappers only give the demo and tests a small named vocabulary. Do not reimplement the
maths here — fix it in the pipeline and re-run the sync.

All shifts follow the project SUBTRACT convention: a returned ``(dx, dy, dz)`` is the
moving→reference DISPLACEMENT, i.e. ``ref_coord = mov_coord − shift``.
"""
from __future__ import annotations

import numpy as np

from ._synced import (
    CrossSessionFOVResult,
    match_boutons_cross_session,
    register_fov_xy,
    register_zstack_3d,
)

FOVShift = CrossSessionFOVResult          # the (dx, dy, dz, peak, is_same_fov) result


def register_2d(ref_img, mov_img, *, upsample_factor: int = 10):
    """2-D FOV registration from two reference IMAGES (mean/STD projections).

    Returns ``(dx, dy, peak_corr)`` — the moving→reference xy shift + the post-alignment
    correlation peak ∈ [0, 1]. Recovers no z (that is the point of the 3-D version)."""
    return register_fov_xy(np.asarray(ref_img, float), np.asarray(mov_img, float),
                           upsample_factor=upsample_factor)


def register_3d(ref_stack, mov_stack, *, upsample_factor: int = 4, enhance: bool = True):
    """Full 3-D FOV registration from two z-STACKS (z, y, x).

    With ``enhance=True`` a Sato **vesselness** filter first locks onto the tubular axon
    arbor — a structural fingerprint far more stable across days than the activity-dependent
    mean image. Returns a :class:`FOVShift` carrying ``dx, dy, dz_planes`` and the 3-D peak."""
    return register_zstack_3d(np.asarray(ref_stack, float), np.asarray(mov_stack, float),
                              upsample_factor=upsample_factor, enhance=enhance)


def match_boutons(ref_centroids, mov_centroids, shift, *, radius_px: float = 4.0,
                  z_radius_planes: float = 1.0):
    """Match boutons across two sessions given a :class:`FOVShift`.

    ``*_centroids`` are ``(N, 3)`` ``[x, y, z]`` (or ``(N, 2)`` for xy-only). Applies the
    SUBTRACT convention (``mov − shift``) then greedily pairs each reference bouton to its
    nearest moving bouton within ``radius_px`` (and ``z_radius_planes`` in z). Returns
    ``[(ref_i, mov_j), ...]``. The boutons that DON'T match under an xy-only (dz=0) shift but
    DO under the recovered 3-D shift are the z-jitter cost that 3-D registration pays back."""
    return match_boutons_cross_session(
        np.asarray(ref_centroids, float), np.asarray(mov_centroids, float),
        shift, radius_px=radius_px, z_radius_planes=z_radius_planes)
