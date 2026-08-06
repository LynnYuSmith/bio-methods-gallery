import numpy as np

from make_sample import make_movie
from tracetrust import assess


def test_each_bouton_gets_its_true_verdict():
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois)
    assert res["stable"]["verdict"] == "trustworthy"
    assert res["xy_drift"]["verdict"] == "residual-motion"
    assert res["z_drift"]["verdict"] == "z-drift"


def test_xy_drift_shows_residual_shift_the_others_dont():
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois)
    assert res["xy_drift"]["residual_shift_px"] > 2.0        # patch really moves
    assert res["stable"]["residual_shift_px"] < 1.0
    assert res["z_drift"]["residual_shift_px"] < 1.0         # z-drift does NOT move in xy


def test_zdrift_dims_faster_than_the_field_but_stable_does_not():
    # the whole point: z-drift is separable from FOV-wide photobleaching
    stack, rois, fps, truth = make_movie(seed=0)
    res = assess(stack, rois)
    assert res["z_drift"]["zdrift_excess"] > 0.3            # dims well beyond the FOV bleaching
    assert res["stable"]["zdrift_excess"] < 0.15           # tracks the field
    # and the z-drift bouton's apparent "silence" is a big resting-level drop
    assert res["z_drift"]["frac_decline"] > 0.5


def test_false_silence_is_not_called_real_silence():
    # a z-drifting bouton looks quiet (large resting drop) but must NOT read as trustworthy —
    # its quiet is an artifact of leaving the plane, which is exactly what the verdict says.
    stack, rois, fps, truth = make_movie(seed=1)
    res = assess(stack, rois)
    assert res["z_drift"]["verdict"] == "z-drift"
    assert res["z_drift"]["verdict"] != "trustworthy"
