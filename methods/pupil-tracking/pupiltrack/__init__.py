"""Run a per-frame pupil detector across a video with temporal consistency.

Two layers, two owners:

* ``detect.py`` — the per-frame pupil detector (threshold the dark pupil, take the
  largest dark blob, report centre and equivalent radius). This is Sonja Nevelchuk's
  algorithm, used here with her permission and re-implemented in NumPy/SciPy for a
  self-contained demo.
* ``track.py`` — the tracking tool (Lynn Smith), the contribution this tile shows:
  it turns the detector's frame-by-frame guesses into one clean pupil-size trace.
"""
from .detect import detect_candidates, detect_pupil
from .track import track_pupil

__all__ = ["detect_pupil", "detect_candidates", "track_pupil"]
