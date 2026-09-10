"""What the tile claims, as tests.

Each test pins one claim from the README, so a change that breaks a claim fails here rather
than quietly making the figure a lie.
"""
import numpy as np

from make_sample import make_eye_video
from pupiltrack import detect_border, detect_brightest_blob, detect_pupil, track_pupil


def test_border_measures_a_clean_frame():
    frames, truth = make_eye_video(seed=0)
    det = detect_pupil(frames[0])                  # frame 0: no blink, no glare overlap
    assert det is not None
    cy, cx, r = det
    assert abs(cy - frames.shape[1] / 2) < 8
    assert abs(cx - frames.shape[2] / 2) < 8
    assert abs(r - truth["radius"][0]) < 1.5       # the border, not the blob


def test_border_beats_the_blob_on_accuracy():
    frames, truth = make_eye_video(seed=0)
    gt = truth["radius"]
    blob = np.array([(detect_brightest_blob(f) or (np.nan,) * 3)[2] for f in frames])
    border = track_pupil(frames)["radius"]
    e_blob = np.nanmedian(np.abs(blob - gt))
    e_border = np.nanmedian(np.abs(border - gt))
    assert e_border < e_blob / 2, (e_border, e_blob)


def test_the_blob_inflates_where_glare_covers_the_border():
    """The failure the tile exists to show, and the two different ways to fail.

    Where the saturating glare band lies across the pupil's border, the bright REGION is the
    pupil and the band together: the blob's equivalent radius grows and it reports that number
    with no sign that anything went wrong. The border method cannot see the occluded arc, so it
    refuses those frames. Wrong-and-confident against declining to answer — which is the whole
    argument for measuring a border rather than an area.
    """
    frames, truth = make_eye_video(seed=0)
    gt = truth["radius"]
    glare = np.asarray([i for i in truth["glare"] if i not in set(truth["blinks"])])
    assert len(glare) > 5
    blob = np.array([(detect_brightest_blob(f) or (np.nan,) * 3)[2] for f in frames])
    tracked = track_pupil(frames)
    border = tracked["radius"]

    blob_err = np.abs(blob[glare] - gt[glare])
    assert np.isfinite(blob_err).all()                 # it answers every time
    assert np.nanmax(blob_err) > 3.0, np.nanmax(blob_err)

    refused = [i for i in glare if tracked["status"][i] != "measured"]
    assert len(refused) > len(glare) / 2, tracked["status"][glare]
    # and where it does answer on those frames, it is not wrong by much
    kept = np.abs(border[glare] - gt[glare])
    kept = kept[np.isfinite(kept)]
    if len(kept):
        assert kept.max() < 2.5, kept.max()


def test_blinks_are_refused_not_guessed():
    frames, truth = make_eye_video(seed=0)
    tracked = track_pupil(frames)
    for b in truth["blinks"]:
        assert tracked["status"][b] != "measured", (b, tracked["status"][b])


def test_short_gaps_are_interpolated_and_marked_as_such():
    frames, truth = make_eye_video(seed=0)
    tracked = track_pupil(frames)
    filled = [b for b in truth["blinks"] if tracked["status"][b] == "interpolated"]
    assert filled, tracked["status"][truth["blinks"]]
    for b in filled:
        assert np.isfinite(tracked["radius"][b])


def test_anchoring_keeps_the_measurement_on_the_pupil():
    frames, _ = make_eye_video(seed=0)
    tr = track_pupil(frames)
    cy = tr["cy"][np.isfinite(tr["cy"])]
    assert len(cy) > 100
    assert abs(np.median(cy) - frames.shape[1] / 2) < 6   # never captured by the lid band


def test_a_refusal_carries_its_reason():
    frames, truth = make_eye_video(seed=0)
    r = detect_border(frames[truth["blinks"][0]])
    assert r["status"] != "ok"
    assert r["status"] in {"no_centre", "no_contrast", "few_rays", "short_arc", "poor_fit"}
    assert np.isnan(r["radius"])


def test_a_crossing_at_the_window_edge_is_not_a_border():
    """The dangerous failure: a tight window whose dark corners fit a clean circle to nothing.

    A frame cropped so tightly that the pupil fills it has no iris to fall into, so the method
    must refuse rather than return the window's own size.
    """
    frames, truth = make_eye_video(seed=0)
    f = frames[0]
    cy, cx = f.shape[0] // 2, f.shape[1] // 2
    r = int(truth["radius"][0])
    tight = f[cy - r + 2:cy + r - 2, cx - r + 2:cx + r - 2]   # inside the pupil only
    out = detect_border(tight)
    assert out["status"] != "ok", out


def test_zero_and_uniform_frames_do_not_raise():
    z = np.zeros((40, 50))
    assert detect_border(z)["status"] != "ok"
    assert detect_pupil(z) is None
    assert detect_brightest_blob(z) is None
    flat = np.full((40, 50), 128.0)
    assert detect_border(flat)["status"] != "ok"
