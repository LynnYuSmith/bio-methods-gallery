"""Trace trustworthiness after 2-D motion correction: is the ROI still measuring the same bouton?

Suite2p corrects x and y but not z. Two failure modes survive it, and both make a trace lie:

* **residual xy motion** — the ROI keeps sliding across the sensor, mixing in neighbouring
  pixels. Caught by tracking the bouton's patch over time with the real pipeline registration
  engine (``register_fov_xy``): the residual displacement grows bin after bin.
* **z-drift** — the bouton drifts out of the focal plane, dims, and its trace reads as going
  quiet even though the cell never changed its firing. Caught by comparing the bouton's own
  resting-fluorescence decline to the FOV-wide decline (photobleaching): a bouton that dims
  *faster than the field*, while its patch stays put, is z-drifting — a false silence, not a
  real one. The z-drift detector is the tile's own contribution.

``register_fov_xy`` is an independent COPY of the pipeline function, synced into ``_synced.py``
by ``_sync/sync.py``. Fix the maths in the pipeline, then re-run the sync.
"""
from .trust import assess, residual_xy, resting_f, roi_trace

__all__ = ["assess", "residual_xy", "resting_f", "roi_trace"]
