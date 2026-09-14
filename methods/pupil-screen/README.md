# pupil-screen

Measure the pupil from a region of the **screen**, when the camera cannot be opened twice — and
know when there is nothing to measure.

## Why capture a screen at all

A USB-3 machine-vision camera belongs to whichever process opens it first. While the vendor's
viewer is recording, nothing else can read that camera: not another process, not another user,
not a script. On an offline acquisition PC with no admin rights, adding a second acquisition
path is not an option either.

What is always available is the screen. The viewer is already drawing the eye. A region of that
window can be captured by anything, at any time, without touching the camera or disturbing the
recording — which makes it possible to watch an instrument you are not allowed to open.

## The part that matters: knowing when not to measure

Most rigs light the eye only while they record. Between recordings the region is dark.

A pupil detector handed a dark frame **does not refuse it**. It finds the brightest thing
present — sensor noise — and returns a diameter and a confidence, and the log fills with
measurements of darkness that are formatted exactly like measurements of a pupil. Afterwards
nothing can separate them.

`LaserGate` learns the two brightness levels from what it has seen — the midpoint between the
darkest and brightest is the threshold, with ±10 % hysteresis so a region sitting at the edge
cannot flap — and reports the instrument as idle while the region is dark. The measurement is
then not attempted at all: the row says `laser_off`, and a gap in a log is honest in a way a
confident wrong number never is.

```
$ python examples/demo.py
  360 frames, 120 of them with the rig idle

  without the gate, the idle frames are measured anyway:
    120 'measurements' of darkness, median 69.8 px, range 68.8-70.9
    real pupils in the same session: median 31.0 px, range 14.6-38.1
    0 of the 120 land inside the real range, though every one of them is reported as a measurement

  with the gate, those frames are gaps:
    120 rows of status=laser_off, 240 measurements, 2 recording epochs found
```

Whether a fabricated value happens to *look* plausible depends on the detector: this stand-in
reads noise as a huge pupil, while a threshold-based one reads it as a tiny one and lands
squarely inside the real range. What is true of both is that the row carries a diameter and a
status of `ok`.

The gate also counts **epochs** — each idle→recording transition. That is the caller's signal
to forget where the pupil was: between recordings the animal has had minutes to look elsewhere,
and an anchored search that carries its old position across the gap starts the next recording
hunting in the wrong place.

## Regions, and one grab for all of them

```python
from pupilscreen import Roi, RoiSet, run_stream

rois = RoiSet([
    Roi("pupil",  (110, 55, 200, 140)),   # measured
    Roi("laser",  (10, 10, 90, 60)),      # decides whether the rig is running
    Roi("motion", (220, 80, 300, 160)),   # frame-to-frame movement, logged alongside
])

for row in run_stream(frames, rois, my_detector):
    ...
```

Two decisions worth naming:

**A separate region for the brightness test.** A tight crop on a dilated pupil barely dims when
the illumination goes off, so it is a poor witness to whether a recording is running. Without a
`laser` region the pupil's own is used, which is what a one-region setup has to do.

**Every region is cut from one grab of their bounding box**, not grabbed separately. Regions
captured one at a time drift apart by however long the capture takes, and a pupil compared with
a whisker movement measured 40 ms later is a comparison of two moments dressed up as one.

The box convention is `(x0, y0, x1, y1)`, cropping as `frame[y0:y1, x0:x1]`, everywhere. Mixing
the two orders yields a picture of *somewhere*, which is why it never announces itself.

## What capturing a screen costs you

None of these are free, and all of them are silent:

**Scale.** A diameter measured here is in SCREEN pixels. A viewer at 2:1 zoom makes one sensor
pixel two screen pixels, so a px/mm figure taken from the sensor is wrong by the zoom factor.
Measure the scale on screen at the zoom in use, or report pixels and stop.

**The display's own contrast.** A border-fitting pupil method reads a radial profile — a
saturated plateau, a cliff, the darker trough of the iris — and a display LUT or auto-gain
rewrites exactly that. `profile_health` returns those three numbers for every frame so the
failure is visible rather than invisible: compare them against the same numbers taken from the
recorded video, and if they disagree, the screen is not showing you the data.

**Resolution.** Zoom the viewer *in* before measuring. A ten-pixel pupil displayed at 1:2
arrives as five pixels, and there is no profile left to read.

## What this is not

It is a way to observe an instrument, not to record one. There are no camera timestamps here,
only the rate at which the screen happens to update. For numbers that go into an analysis,
measure the recorded video, where every frame carries its own timing — this module pairs
naturally with [`pupil-tracking`](../pupil-tracking), which is the measurement itself.

## Install and test

```bash
pip install -e .
pytest -q                 # 17 tests
python examples/demo.py   # the gate, with and without
```

Dependencies: `numpy`, `opencv-python`. Screen capture in your own driver needs `mss` or
Pillow; this module takes frames from wherever you get them and never grabs anything itself,
which is also what makes it testable.
