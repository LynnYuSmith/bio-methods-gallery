import numpy as np
import pytest

from make_sample import write_synthetic_mesc
from mescreader import list_units, read_frames, read_metadata, mesc_to_hdf5, mesc_to_tiff


@pytest.fixture
def mesc(tmp_path):
    path = tmp_path / "synthetic.mesc"
    truth = write_synthetic_mesc(path, n_units=2, frames=20, height=32, width=40, n_channels=2)
    return path, truth


def test_list_units_reads_the_layout(mesc):
    path, truth = mesc
    units = list_units(path)
    assert [u["path"] for u in units] == ["MSession_0/MUnit_0", "MSession_0/MUnit_1"]
    u = units[0]
    assert u["channels"] == ["Channel_0", "Channel_1"]
    assert u["frames"] == 20 and u["height"] == 32 and u["width"] == 40
    assert abs(u["frame_rate_hz"] - 30.0) < 1e-6           # from the Z-axis ms/frame scale


def test_read_frames_is_raw_and_exact(mesc):
    path, truth = mesc
    arr = read_frames(path, "MSession_0/MUnit_0", "Channel_0")
    assert arr.dtype == np.uint16                          # stored dtype, unchanged
    assert np.array_equal(arr, truth["MSession_0/MUnit_0"]["Channel_0"])   # bit-identical


def test_tiff_roundtrip_is_bit_identical(mesc, tmp_path):
    import tifffile
    path, truth = mesc
    written = mesc_to_tiff(path, tmp_path / "tiff")
    assert len(written) == 4                               # 2 units x 2 channels
    back = tifffile.imread(tmp_path / "tiff" / "MSession_0_MUnit_1_Channel_0.tif")
    assert np.array_equal(back, truth["MSession_0/MUnit_1"]["Channel_0"])


def test_hdf5_roundtrip_preserves_frames_and_metadata(mesc, tmp_path):
    import h5py
    path, truth = mesc
    out = mesc_to_hdf5(path, tmp_path / "out.h5")
    with h5py.File(out, "r") as f:
        assert np.array_equal(f["MSession_0/MUnit_0/Channel_1"][:],
                              truth["MSession_0/MUnit_0"]["Channel_1"])
        g = f["MSession_0/MUnit_0"]
        assert int(g.attrs["ZDim"]) == 20                 # acquisition attrs travel with the frames
        assert "Channel_0_Conversion_ConversionLinearOffset" in g.attrs


def test_conversion_offset_is_reported_not_applied(mesc):
    # "as-is" — the linear conversion is metadata only; the stored counts are returned untouched
    path, truth = mesc
    meta = read_metadata(path, "MSession_0/MUnit_0")
    assert "Channel_0_Conversion_ConversionLinearOffset" in meta
    arr = read_frames(path, "MSession_0/MUnit_0", "Channel_0")
    assert arr.min() >= 0                                  # raw counts, no offset subtracted
    assert np.array_equal(arr, truth["MSession_0/MUnit_0"]["Channel_0"])
