"""Write a minimal synthetic .mesc file — the Femtonics MESc layout, as HDF5.

A MESc file is an HDF5 with ``/MSession_i/MUnit_j`` groups; each unit carries acquisition
attributes (dimensions, frame timing, pixel size, per-channel conversion) and one 3-D dataset
per channel, ``Channel_k`` of shape ``(frames, height, width)``. This makes a tiny one with a
known frame pattern so a round-trip (convert → read back) can be checked against ground truth.
"""
import datetime

import h5py
import numpy as np


def write_synthetic_mesc(path, *, n_units=2, frames=20, height=32, width=40, n_channels=2,
                         frame_rate_hz=30.0, pixel_um=1.5, seed=0):
    """Write a synthetic .mesc and return ground truth ``{unit_path: {channel: frames_array}}``."""
    rng = np.random.RandomState(seed)
    z_scale_ms = 1000.0 / frame_rate_hz
    truth = {}
    with h5py.File(str(path), "w") as f:
        f.attrs["MESc"] = "synthetic"                      # a harmless file-level marker
        sess = f.create_group("MSession_0")
        for j in range(n_units):
            unit = sess.create_group(f"MUnit_{j}")
            unit.attrs["ZDim"] = frames
            unit.attrs["XDim"] = width
            unit.attrs["YDim"] = height
            unit.attrs["ZAxisConversionConversionLinearScale"] = z_scale_ms      # ms / frame
            unit.attrs["XAxisConversionConversionLinearScale"] = pixel_um        # µm / px
            unit.attrs["YAxisConversionConversionLinearScale"] = pixel_um
            unit.attrs["VecChannelsSize"] = n_channels
            unit.attrs["CommentDebugString"] = f"unit {j} - synthetic".encode("utf-8")
            unit.attrs["MeasurementDatePosix"] = int(
                datetime.datetime(2026, 1, 1, 12, 0, j).timestamp())
            upath = f"MSession_0/MUnit_{j}"
            truth[upath] = {}
            for k in range(n_channels):
                # a distinct, known pattern per unit/channel: a moving bright square + noise
                arr = rng.randint(50, 120, size=(frames, height, width)).astype(np.uint16)
                for t in range(frames):
                    y0 = (2 + t) % (height - 6)
                    x0 = (3 + 2 * t + 5 * k + 7 * j) % (width - 6)
                    arr[t, y0:y0 + 6, x0:x0 + 6] += np.uint16(800 + 100 * k)
                unit.create_dataset(f"Channel_{k}", data=arr, compression="gzip")
                unit.attrs[f"Channel_{k}_Conversion_ConversionLinearOffset"] = -393 - k
                truth[upath][f"Channel_{k}"] = arr
    return truth


if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    p = Path(tempfile.mkdtemp()) / "synthetic.mesc"
    t = write_synthetic_mesc(p)
    print(f"wrote {p} — units {list(t)}, channels/unit {list(next(iter(t.values())))}")
