"""Read a Femtonics .mesc file and convert it, raw, to TIFF or HDF5 — no correction, nothing.

A .mesc is an HDF5 with ``/MSession_i/MUnit_j`` groups; each unit has acquisition attributes and
one 3-D dataset per channel, ``Channel_k`` shaped ``(frames, height, width)``. This lists the
units, reads any channel's frames exactly as stored, and writes them out unchanged — one TIFF
stack per unit/channel, or a plain HDF5 mirror — carrying the metadata so nothing is lost. The
per-channel linear conversion is reported but never applied: "as-is" means the stored values.
"""
from .read import list_units, mesc_to_hdf5, mesc_to_tiff, read_frames, read_metadata

__all__ = ["list_units", "read_metadata", "read_frames", "mesc_to_tiff", "mesc_to_hdf5"]
