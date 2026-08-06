import numpy as np

from make_sample import make_traces
from traceqc import snr, photobleaching


def test_snr_separates_clean_from_noisy_on_dff():
    s = make_traces(seed=0)
    clean = snr(s["clean"], fs=s["fps"])
    noisy = snr(s["noisy"], fs=s["fps"])
    assert clean["snr_peak"] > 4.0                 # same events, but clean ΔF/F
    assert noisy["snr_peak"] < 3.0                 # buried in noise
    assert clean["snr_peak"] > noisy["snr_peak"]
    assert clean["grade"] < noisy["grade"]          # 'B' < 'D' (A is best), grade follows SNR


def test_photobleaching_detected_on_raw_only_when_present():
    s = make_traces(seed=0)
    bl = photobleaching(s["raw_bleached"], fs=s["fps"])
    st = photobleaching(s["raw_stable"], fs=s["fps"])
    # a real decay: good r² and a large %/min
    assert bl["fit_success"] and bl["r_squared"] > 0.5 and bl["decay_rate"] > 20.0
    # a stable trace: the r² gate rejects the fit even though curve_fit returns something
    assert st["r_squared"] < 0.5


def test_the_two_gates_live_on_different_representations():
    # SNR is meaningful on ΔF/F; photobleaching is meaningful on raw F. Each gate uses the
    # representation it is designed for — that is the whole point of pairing them.
    s = make_traces(seed=0)
    assert np.isfinite(snr(s["clean"], fs=s["fps"])["snr_peak"])          # SNR on ΔF/F
    assert photobleaching(s["raw_bleached"], fs=s["fps"])["r_squared"] > 0.5  # bleach on raw F


def test_snr_grade_maps_from_quality_score():
    s = make_traces(seed=1)
    from traceqc._synced import QualityGrade
    r = snr(s["clean"], fs=s["fps"])
    assert r["grade"] == QualityGrade.from_score(r["quality_score"]).value
