"""Measure the pupil by fitting its BORDER, and track that across a video.

Two layers:

* ``detect.py`` — the per-frame measurement for bright-pupil (coaxial IR) video: rays cast from
  an anchored centre to the half-drop between the pupil's saturated plateau and the iris
  trough, a least-squares circle through the crossings whose fall held, and a REFUSAL when the
  fit does not earn its residual and visible arc. This is the method used in the dissertation
  this gallery draws from.
* ``track.py`` — the temporal layer: anchoring the search on the previous centre so a brighter
  structure elsewhere cannot capture it, re-acquiring after a blink, bridging only short gaps,
  and refusing transient diameter jumps rather than smoothing them.

An earlier version of this tile demonstrated the temporal layer on a DARK-pupil blob detector
(Sonja Nevelchuk's algorithm, used with permission). That detector suited a different imaging
regime and is no longer part of the tile; the method shown now is the bright-pupil border fit.
"""
from .detect import (detect_border, detect_brightest_blob, detect_pupil, fit_circle,
                     pupil_centre)
from .track import track_pupil

__all__ = ["detect_border", "detect_pupil", "detect_brightest_blob", "pupil_centre",
           "fit_circle", "track_pupil"]
