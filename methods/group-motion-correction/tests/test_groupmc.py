"""Tests for groupmc: a shared reference brings drifted recordings into register."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
from make_sample import make_sample                      # noqa: E402
from groupmc import group_motion_correct, correct_tiffs  # noqa: E402


def _drifted(scene, dy, dx, n=8):
    return np.stack([np.roll(np.roll(scene, dy, 0), dx, 1).astype("float32")] * n)


def test_shared_reference_reduces_cross_recording_offset():
    rng = np.random.RandomState(0)
    scene = rng.standard_normal((48, 48)).astype("float32")
    stacks = [_drifted(scene, 0, 0), _drifted(scene, 3, -2), _drifted(scene, -2, 4)]
    registered, ref, shifts = group_motion_correct(stacks)
    # after registration every recording's mean matches the reference much better than before
    before = [np.abs(s.mean(0) - ref).mean() for s in stacks]
    after = [np.abs(r.mean(0) - ref).mean() for r in registered]
    for b, a in zip(before[1:], after[1:]):               # recordings 1,2 were offset
        assert a < b * 0.5


def test_reported_shifts_match_injected_roll_in_subtract_sign():
    # A roll of (dy, dx) must be REPORTED as (dy, dx) — the pipeline's SUBTRACT convention
    # (moving→reference displacement), NOT its negative. The offset test above only checks the
    # registered FRAMES, so a sign flip on the persisted shift (the MC-quality evidence) would
    # ship green there; assert the shift VALUES here so a mirror fails loudly.
    rng = np.random.RandomState(0)
    scene = rng.standard_normal((48, 48)).astype("float32")
    _reg, _ref, shifts = group_motion_correct([_drifted(scene, 0, 0), _drifted(scene, 3, -2)])
    dy, dx = float(shifts[1][0][0]), float(shifts[1][0][1])
    assert abs(dy - 3.0) < 0.2, dy          # == +3, not -3
    assert abs(dx - (-2.0)) < 0.2, dx        # == -2, not +2


def test_mismatched_frame_sizes_raise():
    with pytest.raises(ValueError):
        group_motion_correct([np.zeros((4, 10, 10), "float32"),
                              np.zeros((4, 10, 12), "float32")])


def test_correct_tiffs_writes_tiff_and_hdf5(tmp_path):
    import h5py
    raw = make_sample(tmp_path / "raw", n_recordings=2, n_frames=6)
    result = correct_tiffs(raw, tmp_path / "out")
    assert Path(result["hdf5"]).exists()
    assert all(Path(t).exists() for t in result["tiffs"])
    with h5py.File(result["hdf5"], "r") as f:
        assert "reference" in f
        assert set(f["units"]) == {"recording_0", "recording_1"}
        assert f["units/recording_0/motion_shifts"].shape[1] == 2
