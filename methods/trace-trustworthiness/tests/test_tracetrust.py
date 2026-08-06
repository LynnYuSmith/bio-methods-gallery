import numpy as np

from make_sample import make_movie
from tracetrust import assess


def test_residual_motion_is_movement_locked():
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois, fps, run=truth["run"])
    # every bouton's residual motion tracks the running trace
    for name in rois:
        assert res[name]["run_corr"] > 0.5, (name, res[name]["run_corr"])


def test_present_boutons_keep_a_high_presence():
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois, fps, run=truth["run"])
    for name in rois:
        if name == truth["disappears"]:
            continue
        assert not res[name]["disappeared"]
        assert res[name]["presence"].min() > 0.7        # stays matchable throughout


def test_the_disappearing_bouton_is_caught():
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois, fps, run=truth["run"])
    gone = res[truth["disappears"]]
    assert gone["disappeared"]                          # flagged as leaving the FOV
    assert gone["presence"].min() < 0.2                 # presence collapses (ROI reads background)
    assert gone["max_shift_px"] > 6.0                   # shoved well out of its ROI


def test_disappearance_happens_during_a_bout_not_at_rest():
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois, fps, run=truth["run"])
    gone = res[truth["disappears"]]["gone_flag"]
    run = truth["run"]
    # the frames where the bouton is gone are running frames, not resting ones
    assert run[gone].mean() > run[~gone].mean()
    assert run[gone].mean() > 0.3
