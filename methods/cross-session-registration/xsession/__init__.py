"""Cross-session FOV registration: match the same field of view across DAYS in 3-D.

Re-imaging the same cortical patch on another day, the field of view lands at a slightly
different (x, y) AND a different z-depth (the focal plane never returns to exactly the same
place). The activity-dependent MEAN image also drifts day to day, so registering on
brightness is unreliable. The fix here registers the whole z-STACK in 3-D on a **vesselness
fingerprint** of the axon arbor — the tubular structure is stable across days — recovering
all three axes at once, so the same physical bouton is the same coordinate on every day.

The payoff is measurable: after 3-D registration you can MATCH the same boutons across days;
a 2-D-only (dz = 0) shift silently drops the z-jittered ones. That drop, recovered, is the tile.

The estimators are independent COPIES of the real lab-pipeline functions (``register_fov_xy``,
``register_zstack_3d``, ``match_boutons_cross_session``), synced verbatim into ``_synced.py``
by ``_sync/sync.py`` and wrapped here. Fix the maths in the pipeline, then re-run the sync.
"""
from .register import FOVShift, match_boutons, register_2d, register_3d

__all__ = ["register_2d", "register_3d", "match_boutons", "FOVShift"]
