"""The gate must pause on darkness, and the regions must describe one instant."""
import numpy as np
import pytest

from pupilscreen import LaserGate, Roi, RoiSet, profile_health, run_stream


def lit_frame(v=200, shape=(30, 40)):
    return np.full(shape, v, np.uint8)


# --------------------------------------------------------------------------- the gate
def test_the_gate_stays_shut_until_it_has_seen_light():
    """With only dark frames there is no split to find, so the floor decides."""
    gate = LaserGate()
    assert [gate.update(b) for b in (1, 2, 3, 2)] == [False] * 4
    assert gate.epoch == 0


def test_the_gate_opens_on_a_recording_and_counts_it():
    gate = LaserGate()
    for b in (2, 2, 2):
        gate.update(b)
    assert gate.update(95) is True
    assert gate.epoch == 1
    for b in (2, 2):
        gate.update(b)
    assert gate.on is False
    assert gate.update(95) is True
    assert gate.epoch == 2, "each recording is its own epoch"


def test_the_threshold_settles_between_the_two_levels():
    gate = LaserGate()
    for b in [3] * 30 + [100] * 30:
        gate.update(b)
    assert 40 < gate.threshold < 60, f"threshold {gate.threshold} is not between 3 and 100"


def test_hysteresis_keeps_a_region_at_the_edge_from_flapping():
    """A brightness sitting exactly on the threshold must not toggle every frame."""
    gate = LaserGate()
    for b in [3] * 20 + [100] * 20:
        gate.update(b)
    thr = gate.threshold
    states = [gate.update(thr + d) for d in (0.5, -0.5, 0.5, -0.5, 0.5, -0.5)]
    assert len(set(states)) == 1, f"the gate flapped: {states}"


def test_an_override_forces_the_gate_and_keeps_counting():
    gate = LaserGate(override=True)
    assert gate.update(0) is True, "override=True must measure even a black region"
    assert LaserGate(override=False).update(255) is False


# --------------------------------------------------------------------------- the regions
def test_a_box_is_x0_y0_x1_y1_and_crops_rows_by_y():
    img = np.arange(20 * 30, dtype=np.uint16).reshape(20, 30)
    r = Roi("pupil", (5, 2, 9, 6))
    assert r.width == 4 and r.height == 4
    assert np.array_equal(r.crop(img), img[2:6, 5:9]), "x and y were swapped"


@pytest.mark.parametrize("box", [(9, 2, 5, 6), (5, 6, 9, 2), (5, 2, 5, 6)])
def test_an_impossible_box_is_refused_at_once(box):
    with pytest.raises(ValueError):
        Roi("pupil", box)


def test_an_unknown_role_is_refused():
    with pytest.raises(ValueError):
        Roi("whiskers", (0, 0, 5, 5))


def test_every_region_is_cut_from_one_grab():
    """The whole point: the regions describe the same instant, not three nearby ones."""
    rois = RoiSet([Roi("pupil", (10, 10, 30, 30)), Roi("laser", (50, 5, 70, 15))])
    assert rois.union() == (10, 5, 70, 30)
    big = np.zeros((25, 60), np.uint8)
    big[5:25, 0:20] = 7                       # the pupil region, in union coordinates
    big[0:10, 40:60] = 200                    # the laser region
    cuts = rois.cut_all(big)
    assert cuts[0].shape == (20, 20) and int(cuts[0].mean()) == 7
    assert cuts[1].shape == (10, 20) and int(cuts[1].mean()) == 200


def test_the_brightness_witness_prefers_its_own_region():
    """A tight crop on a dilated pupil is a poor witness to whether the rig is running."""
    pupil_only = RoiSet([Roi("pupil", (0, 0, 10, 10))])
    assert pupil_only.brightness_source().role == "pupil"
    both = RoiSet([Roi("pupil", (0, 0, 10, 10)), Roi("laser", (20, 0, 30, 10))])
    assert both.brightness_source().role == "laser"
    assert RoiSet().brightness_source() is None


# --------------------------------------------------------------------------- the profile
def test_the_profile_reports_a_plateau_above_a_trough():
    img = np.full((40, 40), 70, np.uint8)
    yy, xx = np.mgrid[0:40, 0:40]
    img[np.hypot(xx - 20, yy - 20) < 9] = 250
    h = profile_health(img)
    assert h["plateau"] > 200 and h["trough"] < 100
    assert h["contrast"] == pytest.approx(h["plateau"] - h["trough"])


def test_a_flattened_display_shows_up_as_lost_contrast():
    """What a display LUT does to the profile, and why it is reported every frame."""
    img = np.full((40, 40), 70, np.uint8)
    yy, xx = np.mgrid[0:40, 0:40]
    img[np.hypot(xx - 20, yy - 20) < 9] = 250
    flattened = (img.astype(float) * 0.15 + 100).astype(np.uint8)
    assert profile_health(flattened)["contrast"] < profile_health(img)["contrast"] / 4


# --------------------------------------------------------------------------- the stream
def test_the_stream_measures_only_while_the_region_is_lit():
    rois = RoiSet([Roi("pupil", (0, 0, 20, 20))])
    frames = [np.zeros((20, 20), np.uint8)] * 3 + [lit_frame(shape=(20, 20))] * 3
    calls = []

    def measure(crop):
        calls.append(crop.mean())
        return {"diameter": 12.0}

    out = list(run_stream(frames, rois, measure))
    assert [r["status"] for r in out] == ["laser_off"] * 3 + ["ok"] * 3
    assert len(calls) == 3, "the detector was run on frames with nothing in them"
    assert all("diameter" not in r for r in out[:3])


def test_the_stream_reports_motion_and_the_epoch():
    rois = RoiSet([Roi("pupil", (0, 0, 20, 20)), Roi("motion", (20, 0, 40, 20))])
    a = np.zeros((20, 40), np.uint8)
    a[:, :20] = 200
    b = a.copy()
    b[:, 20:] = 120                                    # the motion region changes
    out = list(run_stream([a, b], rois, lambda c: {"status": "ok"}))
    assert out[0]["motion_2"] == 0.0
    assert out[1]["motion_2"] > 100
    assert out[-1]["epoch"] == 1


def test_a_stream_without_regions_is_refused_rather_than_guessed():
    with pytest.raises(ValueError):
        list(run_stream([np.zeros((5, 5), np.uint8)], RoiSet(), lambda c: {}))
