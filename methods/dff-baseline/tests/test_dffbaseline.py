import numpy as np

from make_sample import make_trace
from dffbaseline import (
    dff,
    lower_envelope_baseline,
    median_baseline,
    rolling_quantile_baseline,
)


def _dff(kind, s):
    f, fps = s["f"], s["fps"]
    if kind == "median":
        return dff(f, median_baseline(f, fps=fps, win_s=20.0))
    return dff(f, lower_envelope_baseline(f, fps=fps, win_s=20.0, q=0.1))


def test_median_dff_centred_on_zero():
    s = make_trace(seed=0)
    d = _dff("median", s)
    assert abs(np.median(d[s["quiet"]])) < 0.012


def test_envelope_dff_biased_up():
    s = make_trace(seed=0)
    q = s["quiet"]
    d_med, d_env = _dff("median", s), _dff("envelope", s)
    assert np.median(d_env[q]) > np.median(d_med[q])
    assert np.median(d_env[q]) > 0.02


def test_median_preserves_negative_excursions():
    s = make_trace(seed=0)
    d = _dff("median", s)
    # honest two-sided noise: real negative deflections survive
    assert d[s["quiet"]].min() < -0.03


def test_lower_quantile_sits_below_median():
    s = make_trace(seed=1)
    f, fps = s["f"], s["fps"]
    b_med = median_baseline(f, fps=fps, win_s=20.0)
    b_env = rolling_quantile_baseline(f, fps=fps, win_s=20.0, q=0.1)
    assert np.mean(b_env) < np.mean(b_med)


def test_floor_baseline_preserves_events_and_sits_below_median():
    # the suite2p maximin FLOOR hugs the bottom of the trace (below a q~0.5 quantile) so that
    # subtracting it PRESERVES median-height events, instead of subtracting them away.
    from dffbaseline import floor_baseline
    s = make_trace(seed=0)
    f, fps = s["f"], s["fps"]
    b_floor = floor_baseline(f, fps=fps, win_s=20.0)
    b_med = median_baseline(f, fps=fps, win_s=20.0)
    assert np.mean(b_floor) < np.mean(b_med)         # a floor, not a mid-signal quantile
    assert dff(f, b_floor).max() > 0.5               # a median-height event survives subtraction
