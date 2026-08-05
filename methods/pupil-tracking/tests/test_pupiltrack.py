import numpy as np

from make_sample import make_eye_video
from pupiltrack import detect_pupil, track_pupil


def test_detect_finds_pupil():
    frames, truth = make_eye_video(seed=0)
    det = detect_pupil(frames[0])          # frame 0 has no blink; distractor is small
    assert det is not None
    cy, cx, r = det
    assert abs(cy - frames.shape[1] / 2) < 8
    assert abs(cx - frames.shape[2] / 2) < 8
    assert abs(r - truth["radius"][0]) < 3


def test_tracker_beats_naive():
    frames, truth = make_eye_video(seed=0)
    gt = truth["radius"]
    naive = np.array([(detect_pupil(f) or (np.nan, np.nan, np.nan))[2] for f in frames])
    tracked = track_pupil(frames)["radius"]
    err_naive = np.nanmean(np.abs(naive - gt))
    err_tracked = np.nanmean(np.abs(tracked - gt))
    assert err_tracked < err_naive


def test_tracker_fills_blinks():
    frames, truth = make_eye_video(seed=0)
    tracked = track_pupil(frames)["radius"]
    for b in truth["blinks"]:               # isolated single-frame blinks -> interpolated
        assert not np.isnan(tracked[b])


def test_tracker_rejects_distractor():
    frames, _ = make_eye_video(seed=0)
    tr = track_pupil(frames)
    cy = tr["cy"]
    valid = ~np.isnan(cy)
    # the pupil sits near row 48; the corner distractor at row 12 must never win.
    assert np.nanmedian(cy[valid]) > 25
