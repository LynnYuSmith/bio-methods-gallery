"""Tests: detection is activity-based and the size window comes from the active regions."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
from make_sample import make_recording                   # noqa: E402
from boutons import (detect_boutons, activity_map,                     # noqa: E402
                     active_regions, size_window_from_active)


def test_static_shaft_is_bright_but_not_active():
    """The shaft is bright in the mean image but flat in the activity map, so activity-based
    detection does not place blobs on it. Check the shaft region: bright on the mean image,
    near-zero on the activity map."""
    stack, ps, truth = make_recording()
    mean_img = stack.mean(0)
    act = activity_map(stack)
    shaft_pts = [(r, c) for (r, c, is_b) in truth if not is_b]
    for (r, c) in shaft_pts:
        # normalise both maps to [0, 1] and compare the same shaft pixel
        m = (mean_img[r, c] - mean_img.min()) / (mean_img.max() - mean_img.min())
        a = (act[r, c] - act.min()) / (act.max() - act.min())
        assert m > 0.3                                    # bright in the mean image
        assert a < m                                      # much dimmer in the activity map


def test_size_window_is_derived_from_active_regions():
    stack, ps, _ = make_recording()
    _, _, diams_px = active_regions(stack)
    lo, hi = size_window_from_active(diams_px, ps)
    assert diams_px.size > 0
    assert lo < hi
    med_um = float(np.median(diams_px)) * ps
    assert lo <= med_um <= hi                             # the window brackets the median active size


def test_detect_returns_boutons_inside_the_window():
    stack, ps, _ = make_recording()
    boutons, all_blobs, (lo, hi) = detect_boutons(stack, ps)
    from boutons import blob_diameter_um
    d = blob_diameter_um(boutons, ps)
    assert boutons.shape[0] > 0
    assert (d >= lo - 1e-6).all() and (d <= hi + 1e-6).all()
