"""The OSI point estimate — an independent COPY of the pipeline's ``analysis/selectivity``.

OSI = (R_pref − R_orth) / (R_pref + R_orth), with directions folded into orientation
space [0°, 180°) and negative responses rectified to 0 (on zero-centred ΔF/F the
orthogonal response can go negative; without rectification the denominator can vanish and
the most selective cells drop out). Reference: Mazurek, Kager & Van Hooser (2014),
Front. Neural Circuits, DOI:10.3389/fncir.2014.00092.

The maths is synced verbatim into ``_synced.py`` (as ``calculate_osi``) by ``_sync/sync.py``;
this module only exposes it under the tile's ``osi`` name. Fix it in the pipeline, re-sync.
"""
from __future__ import annotations

from ._synced import calculate_osi


def osi(responses, orientations, clip_negative: bool = True) -> float:
    """Orientation Selectivity Index in [0, 1] (``nan`` if undefined) — the real
    ``calculate_osi`` from the pipeline (folded to orientation space, negatives rectified)."""
    return calculate_osi(responses, orientations, clip_negative=clip_negative)
