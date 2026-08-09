"""mescmc: group (concat) motion correction for Femtonics .mesc files — .mesc train in, .mesc out.

Our method: build ONE shared reference from the first (early-tissue) unit, hand it to the whole
concatenated train of repeats, so every frame registers to the same grid. The intensity correction
(PMT offset) is read from the file itself; the max shift is physical (µm) via the file's pixel size.
Production runs this as concat-MC over Suite2p; this is a compact independent implementation plus the
.mesc round-trip.
"""
from .mesc_io import channel_offset, list_units, pixel_size_um, read_channel, write_mesc
from .motion_correct import (
    build_group_reference,
    correct_train,
    group_motion_correct_mesc,
)
from .register import (
    apply_shift,
    build_reference,
    correct_stack,
    estimate_shift,
    residual_motion,
)

__all__ = [
    # group method (the headline)
    "build_group_reference", "correct_train", "group_motion_correct_mesc",
    # registration primitives
    "estimate_shift", "apply_shift", "build_reference", "correct_stack", "residual_motion",
    # .mesc I/O
    "list_units", "pixel_size_um", "channel_offset", "read_channel", "write_mesc",
]
