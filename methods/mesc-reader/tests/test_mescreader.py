import warnings

import numpy as np
import pytest

from make_sample import write_synthetic_mesc
from mescreader import (
    channel_conversion,
    list_units,
    mesc_to_hdf5,
    mesc_to_tiff,
    read_frames,
    read_metadata,
)


@pytest.fixture
def mesc(tmp_path):
    path = tmp_path / "synthetic.mesc"
    truth = write_synthetic_mesc(path, n_units=2, frames=20, height=32, width=40, n_channels=2)
    return path, truth


def _raw(truth, unit, ch):
    return truth[unit][ch]["raw"]


def test_list_units_reads_layout_and_conversions(mesc):
    path, truth = mesc
    units = list_units(path)
    assert [u["path"] for u in units] == ["MSession_0/MUnit_0", "MSession_0/MUnit_1"]
    u = units[0]
    assert u["channels"] == ["Channel_0", "Channel_1"]
    assert u["frames"] == 20 and u["height"] == 32 and u["width"] == 40
    assert abs(u["frame_rate_hz"] - 30.0) < 1e-6
    assert u["conversion"]["Channel_0"] == (1.0, -786.0)     # green PMT offset
    assert u["conversion"]["Channel_1"] == (1.0, -1170.0)    # red PMT offset


def test_conversion_applied_by_default_with_a_loud_warning(mesc):
    path, truth = mesc
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        arr = read_frames(path, "MSession_0/MUnit_0", "Channel_0")
    assert len(w) == 1 and "APPLIED" in str(w[0].message)     # loud, and it says what it did
    raw = _raw(truth, "MSession_0/MUnit_0", "Channel_0")
    assert np.array_equal(arr, np.clip(raw.astype(float) - 786, 0, None).astype(raw.dtype))
    assert arr.mean() < raw.mean()                           # the offset really came off


def test_raw_read_skips_conversion_silently(mesc):
    path, truth = mesc
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        arr = read_frames(path, "MSession_0/MUnit_0", "Channel_0", apply_conversion=False)
    assert len(w) == 0                                       # no warning when not converting
    assert np.array_equal(arr, _raw(truth, "MSession_0/MUnit_0", "Channel_0"))


def test_manual_offset_and_scale_override(mesc):
    path, truth = mesc
    raw = _raw(truth, "MSession_0/MUnit_0", "Channel_1")
    by_hand = read_frames(path, "MSession_0/MUnit_0", "Channel_1", offset=-500, warn=False)
    assert np.array_equal(by_hand, np.clip(raw.astype(float) - 500, 0, None).astype(raw.dtype))


def test_tiff_roundtrip_of_the_converted_frames(mesc, tmp_path):
    import tifffile
    path, truth = mesc
    written = mesc_to_tiff(path, tmp_path / "tiff", warn=False)
    assert len(written) == 4
    raw = _raw(truth, "MSession_0/MUnit_1", "Channel_0")
    expected = np.clip(raw.astype(float) - 786, 0, None).astype(raw.dtype)
    back = tifffile.imread(tmp_path / "tiff" / "MSession_0_MUnit_1_Channel_0.tif")
    assert np.array_equal(back, expected)


def test_hdf5_raw_mode_is_bit_identical_and_records_no_conversion(mesc, tmp_path):
    import h5py
    path, truth = mesc
    out = mesc_to_hdf5(path, tmp_path / "out.h5", apply_conversion=False, warn=False)
    with h5py.File(out, "r") as f:
        assert not bool(f.attrs["conversion_applied"])
        d = f["MSession_0/MUnit_0/Channel_1"]
        assert np.array_equal(d[:], _raw(truth, "MSession_0/MUnit_0", "Channel_1"))
        assert not bool(d.attrs["conversion_applied"])
        assert int(f["MSession_0/MUnit_0"].attrs["ZDim"]) == 20    # acquisition attrs preserved


def test_channel_conversion_defaults_when_attr_absent(tmp_path):
    import h5py
    # a unit with no conversion attrs → falls back to the PMT defaults by channel index
    p = tmp_path / "bare.mesc"
    with h5py.File(p, "w") as f:
        u = f.create_group("MSession_0/MUnit_0")
        u.attrs["ZDim"] = 3
        u.create_dataset("Channel_0", data=np.ones((3, 4, 4), np.uint16) * 1000)
    assert channel_conversion(p, "MSession_0/MUnit_0", "Channel_0") == (1.0, -786.0)
