import warnings

import h5py
import numpy as np
import pytest
from scipy.ndimage import shift as nd_shift

from make_sample import write_synthetic_train
from mescmc import (
    apply_shift,
    build_group_reference,
    channel_offset,
    correct_train,
    estimate_shift,
    group_motion_correct_mesc,
    list_units,
    read_channel,
    residual_motion,
)


@pytest.fixture
def train(tmp_path):
    gt = write_synthetic_train(tmp_path / "raw", n_reps=3, frames=24, height=64, width=64, seed=1)
    return gt


# --- registration primitive -------------------------------------------------

def test_estimate_recovers_a_known_shift():
    rng = np.random.RandomState(0)
    ref = rng.rand(64, 64).astype(np.float32)
    ref[20:44, 20:44] += 3.0                               # some structure
    moved = nd_shift(ref, shift=(3.0, -2.0), order=1, mode="nearest")
    dy, dx = estimate_shift(ref, moved)
    assert abs(dy - 3.0) < 0.5 and abs(dx - (-2.0)) < 0.5   # recovered ~ injected
    back = apply_shift(moved, dy, dx)                        # and undoing it restores the frame
    assert np.corrcoef(back.ravel(), ref.ravel())[0, 1] > 0.98


# --- the group method -------------------------------------------------------

def test_reference_is_built_from_the_first_unit_only(train, monkeypatch):
    import mescmc.motion_correct as mc
    seen = []
    real = mc._registration_frames
    monkeypatch.setattr(mc, "_registration_frames",
                        lambda p, u, c: (seen.append((str(p), u)), real(p, u, c))[1])
    tr = [(p, "MSession_0/MUnit_0") for p in train["paths"]]
    build_group_reference(tr, warn=False)
    assert seen == [(str(train["paths"][0]), "MSession_0/MUnit_0")]   # only the first unit was read


def test_group_correction_lands_every_repeat_on_the_anchor_grid(train):
    tr = [(p, "MSession_0/MUnit_0") for p in train["paths"]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ref = build_group_reference(tr, warn=False)
        results = correct_train(tr, ref, warn=False)
    # each corrected repeat's mean image must sit on the shared reference: tiny residual displacement
    for res in results:
        mean_img = res["Channel_0"].astype(np.float32).mean(0)
        dy, dx = estimate_shift(ref, np.clip(mean_img + res["offset"], 0, None))
        assert np.hypot(dy, dx) < 1.0                        # aligned to the anchor grid


def test_group_correction_reduces_motion_vs_raw(train):
    tr = [(p, "MSession_0/MUnit_0") for p in train["paths"]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ref = build_group_reference(tr, warn=False)
        results = correct_train(tr, ref, warn=False)
    for (p, upath), res in zip(tr, results):
        raw = np.clip(read_channel(p, upath, "Channel_0").astype(np.float32) + res["offset"], 0, None)
        corr = np.clip(res["Channel_0"].astype(np.float32) + res["offset"], 0, None)
        assert residual_motion(corr, reference=ref) < residual_motion(raw, reference=ref)


def test_same_shift_is_applied_to_both_channels(train):
    tr = [(p, "MSession_0/MUnit_0") for p in train["paths"]]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ref = build_group_reference(tr, warn=False)
        res = correct_train(tr, ref, warn=False)[1]           # a non-anchor repeat
    # green and red are the same scene; after the SAME shift they stay aligned to each other
    g = res["Channel_0"].astype(np.float32).mean(0)
    r = res["Channel_1"].astype(np.float32).mean(0)
    dy, dx = estimate_shift(g - g.mean(), r - r.mean())
    assert np.hypot(dy, dx) < 0.6


# --- the file-borne parameters ---------------------------------------------

def test_intensity_offset_is_read_from_the_file_not_hardcoded(tmp_path):
    # write a file with a NON-default offset; channel_offset must return it, not −786
    p = tmp_path / "odd.mesc"
    with h5py.File(p, "w") as f:
        u = f.create_group("MSession_0/MUnit_0")
        u.attrs["Channel_0_Conversion_ConversionLinearOffset"] = -640.0
        u.create_dataset("Channel_0", data=np.ones((3, 8, 8), np.uint16) * 1000)
    assert channel_offset(p, "MSession_0/MUnit_0", "Channel_0") == -640.0


def test_max_shift_um_uses_the_files_pixel_size(train, monkeypatch):
    import mescmc.motion_correct as mc
    captured = {}
    real = mc.build_reference
    def spy(frames, **kw):
        captured.update(kw)
        return real(frames, **kw)
    monkeypatch.setattr(mc, "build_reference", spy)
    tr = [(train["paths"][0], "MSession_0/MUnit_0")]
    build_group_reference(tr, max_shift_um=14.2, warn=False)
    # 14.2 µm / 0.71 µm/px = 20 px
    assert abs(captured["max_shift_px"] - 14.2 / train["pixel_um"]) < 1e-6


# --- the .mesc round-trip ---------------------------------------------------

def test_group_motion_correct_writes_valid_corrected_mesc(train, tmp_path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        outs = group_motion_correct_mesc(train["paths"], tmp_path / "mc", warn=False)
    assert len(outs) == len(train["paths"])
    for out in outs:
        units = list_units(out)
        assert units and units[0]["channels"] == ["Channel_0", "Channel_1"]
        with h5py.File(out, "r") as f:
            u = f["MSession_0/MUnit_0"]
            assert bool(f.attrs["motion_corrected"])
            assert "motion_correction_shifts_yx" in u.attrs                 # self-documenting
            assert u.attrs["Channel_0_Conversion_ConversionLinearOffset"] == -786.0  # preserved
            assert u["Channel_0"].shape[0] == 24
