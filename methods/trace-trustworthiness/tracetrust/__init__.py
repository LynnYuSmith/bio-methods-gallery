"""Per-ROI residual-motion trustworthiness on an already motion-corrected movie.

Global motion correction removes the average frame shift, but the tissue is not rigid: when the
animal runs or moves, each bouton keeps its OWN residual shift (the field moves non-uniformly),
and a big enough bout can push a bouton out of its ROI or out of the focal plane (z) so the ROI
measures background, not the bouton. The question is asked PER ROI, on that bouton's own pixels.

``assess`` registers each ROI's local patch to a still template with the pipeline's
``register_fov_xy`` and reads two things from it per frame: the **residual displacement**
(how far this bouton's pixels shifted after correction) and the **presence** (the post-alignment
correlation peak — it collapses when the bouton has left the FOV laterally or by z-defocus). It
flags untrustworthy frames per bouton, catches boutons that disappear, and — given a running
trace — shows the residual motion is movement-locked.

``register_fov_xy`` is an independent COPY of the pipeline function, synced into ``_synced.py``.
Fix the maths in the pipeline, then re-run the sync.
"""
from .trust import assess, roi_motion

__all__ = ["assess", "roi_motion"]
