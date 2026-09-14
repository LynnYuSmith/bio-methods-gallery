"""Measure the pupil from a region of the SCREEN, and know when there is nothing to measure.

Sometimes the camera cannot be opened at all. A USB-3 machine-vision camera is claimed
exclusively by whichever process opens it first, so while the vendor's own viewer is recording,
nothing else can read that camera — not another process, not another user, not a script. On an
offline acquisition PC with no admin rights, installing a second acquisition path is not an
option either.

What is always available is the screen. The viewer is already drawing the eye; a region of that
window can be captured by anything, at any time, without touching the camera or the recording.

This module is the part of that idea worth keeping: the two pieces that decide whether the
numbers mean anything.

1. :class:`LaserGate` — **is there anything to measure right now?** Most rigs light the eye only
   while they record, so the region is bright during a recording and dark between them. A
   tracker run on the dark frames does not fail loudly; it returns confident measurements of
   nothing, which is far worse than a gap. The gate learns the two levels from what it has
   seen and pauses the measurement while the region is dark.

2. :class:`RoiSet` — **which regions, and what is each for?** One region for the pupil is the
   obvious part. A separate one for the brightness test matters more than it looks: a tight
   crop on a dilated pupil barely changes when the illumination goes off, so it is a poor
   witness to whether a recording is running. Motion regions give whisker or body movement on
   the same clock.

What this module does NOT do is measure the pupil — that is `pupil-tracking`'s job, and any
per-frame measurement can be handed to :func:`run_stream` instead.

**What capturing the screen costs you**, because it is not free and the costs are silent:

* **Scale.** A diameter measured on screen is in SCREEN pixels. A viewer at 2:1 zoom makes one
  sensor pixel two screen pixels, so a px/mm calibration taken from the sensor is wrong by the
  zoom factor. Measure the scale on screen, at the zoom in use, or report pixels and stop.
* **The display's own contrast.** A viewer that applies auto-gain or a display LUT redraws the
  very profile a border-fitting method reads. So :func:`profile_health` reports the plateau,
  the trough and their contrast every frame: compare them against the same numbers taken from
  the recorded video, and if they disagree, the screen is not showing you the data.
* **Resolution.** Zoom the viewer IN before measuring. A ten-pixel pupil displayed at 1:2
  arrives as five pixels and there is no profile left to read.

Screen capture is a way to observe an instrument you are not allowed to open. It is not a way
to record one: for numbers that go into an analysis, measure the recorded video, where the
frames carry their own timing.
"""
from __future__ import annotations

from collections import deque
from typing import Callable, Iterable, Iterator, Optional, Sequence

import numpy as np

__all__ = [
    "LaserGate", "RoiSet", "Roi", "profile_health", "run_stream",
    "BRIGHT_FLOOR", "BRIGHT_SPLIT", "ROLES",
]

BRIGHT_FLOOR = 12.0     # a region this dark carries no image at all, whatever the history says
BRIGHT_SPLIT = 8.0      # dark and lit must differ by this much before a midpoint means anything
BRIGHT_N = 400          # frames of history the threshold is learnt from
HYSTERESIS = 0.10       # ±10 % around the threshold, so a region at the edge cannot flap

ROLES = ("pupil", "laser", "motion")


class LaserGate:
    """Decide whether the instrument is running, from how bright a region is.

    The threshold needs no calibration. Over a session the region is bimodal — a dark level
    between recordings and a lit one during them — so the midpoint between the extremes seen so
    far separates them, and it follows a changed lamp or exposure on its own. Until both levels
    have been seen there is nothing to split, and the fixed floor decides: dark is dark.

    Why this is not a nicety. A pupil tracker handed a black frame does not refuse it. It finds
    *something*, reports a diameter and a confidence, and the log fills with measurements of
    darkness that look exactly like a constricted pupil. A gap in a log is honest; a confident
    wrong number is not, and nothing downstream can tell them apart afterwards.

    Parameters
    ----------
    floor : float
        Brightness below which a region is dark regardless of history.
    n : int
        How many frames of history the threshold is learnt from.
    override : bool or None
        ``True``/``False`` force the gate open or shut; ``None`` (default) decides.

    Examples
    --------
    >>> gate = LaserGate()
    >>> [gate.update(b) for b in (2, 2, 2)]          # dark: nothing to measure
    [False, False, False]
    >>> gate.update(90), gate.update(92)             # the rig starts
    (True, True)
    >>> gate.epoch                                   # one recording seen so far
    1
    """

    def __init__(self, floor: float = BRIGHT_FLOOR, n: int = BRIGHT_N,
                 override: Optional[bool] = None):
        self.floor = float(floor)
        self.override = override
        self.hist: deque = deque(maxlen=int(n))
        self.on = False
        self.epoch = 0
        self.threshold = float(floor)

    def update(self, brightness: float) -> bool:
        """Take one frame's mean brightness; return whether the instrument is running."""
        self.hist.append(float(brightness))
        lo, hi = min(self.hist), max(self.hist)
        self.threshold = (lo + hi) / 2 if (hi - lo) >= BRIGHT_SPLIT else self.floor
        if self.override is not None:
            was, self.on = self.on, bool(self.override)
        else:
            was = self.on
            self.on = (brightness > self.threshold * (1 - HYSTERESIS) if self.on
                       else brightness > self.threshold * (1 + HYSTERESIS))
        if self.on and not was:
            self.epoch += 1
        return self.on


class Roi:
    """A rectangle and what it is for.

    The box is ``(x0, y0, x1, y1)`` and crops as ``frame[y0:y1, x0:x1]`` — the same convention
    throughout, because mixing the two orders is a bug that produces a picture of *somewhere*
    and so never announces itself.
    """

    __slots__ = ("role", "box")

    def __init__(self, role: str, box: Sequence[int]):
        if role not in ROLES:
            raise ValueError(f"role must be one of {ROLES}, not {role!r}")
        x0, y0, x1, y1 = (int(v) for v in box)
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"box must be (x0, y0, x1, y1) with x1 > x0 and y1 > y0: {box}")
        self.role = role
        self.box = (x0, y0, x1, y1)

    @property
    def width(self) -> int:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> int:
        return self.box[3] - self.box[1]

    def crop(self, frame: np.ndarray, origin=(0, 0)) -> np.ndarray:
        """This region of a frame, where ``origin`` is that frame's top-left in box space."""
        x0, y0, x1, y1 = self.box
        ox, oy = origin
        return frame[y0 - oy:y1 - oy, x0 - ox:x1 - ox]

    def __repr__(self) -> str:
        return f"Roi({self.role!r}, {self.box})"


class RoiSet:
    """The regions being watched, and the single grab that serves them all.

    Regions are captured from ONE grab of their bounding box rather than one grab each, so they
    describe the same instant. Separately captured regions drift apart by however long the
    capture takes, and a pupil compared against a whisker movement measured 40 ms later is a
    comparison of two different moments dressed up as one.
    """

    def __init__(self, rois: Iterable[Roi] = ()):
        self.items: list[Roi] = list(rois)

    def add(self, role: str, box: Sequence[int]) -> Roi:
        r = Roi(role, box)
        self.items.append(r)
        return r

    def delete(self, i: int) -> Optional[Roi]:
        return self.items.pop(i) if 0 <= i < len(self.items) else None

    def of_role(self, role: str) -> list[Roi]:
        return [r for r in self.items if r.role == role]

    def union(self) -> Optional[tuple[int, int, int, int]]:
        """One box covering every region, or None when there are none."""
        if not self.items:
            return None
        b = np.array([r.box for r in self.items])
        return (int(b[:, 0].min()), int(b[:, 1].min()),
                int(b[:, 2].max()), int(b[:, 3].max()))

    def brightness_source(self) -> Optional[Roi]:
        """The region the gate should watch: a dedicated one, else the pupil's.

        A tight crop on a dilated pupil is a poor witness — it stays bright when the
        illumination goes off — so a separate region is worth having wherever the layout allows
        one.
        """
        laser = self.of_role("laser")
        if laser:
            return laser[0]
        pupil = self.of_role("pupil")
        return pupil[0] if pupil else None

    def cut_all(self, big: np.ndarray) -> dict[int, np.ndarray]:
        """Every region, cut from one grab of :meth:`union`."""
        u = self.union()
        if u is None:
            return {}
        return {i: r.crop(big, origin=(u[0], u[1])) for i, r in enumerate(self.items)}


def profile_health(crop: np.ndarray, lo_pct: float = 5.0, hi_pct: float = 99.5) -> dict:
    """The plateau, the trough and their contrast — the numbers that say if the screen lies.

    A border-fitting pupil method reads a radial profile: a saturated plateau inside the pupil,
    a cliff, the darker trough of the iris. A display LUT or auto-gain rewrites exactly that.
    Reporting these three every frame turns an invisible failure into a visible one: compare
    them with the same numbers taken from the recorded video, and if they do not match, the
    screen is not showing you the data.

    Examples
    --------
    >>> import numpy as np
    >>> img = np.full((40, 40), 70, np.uint8)
    >>> yy, xx = np.mgrid[0:40, 0:40]
    >>> img[np.hypot(xx - 20, yy - 20) < 8] = 250
    >>> h = profile_health(img)
    >>> h["plateau"] > 200 and h["trough"] < 100 and h["contrast"] > 100
    True
    """
    a = np.asarray(crop, float)
    fin = a[np.isfinite(a)]
    if fin.size < 16:
        return {"plateau": float("nan"), "trough": float("nan"), "contrast": float("nan")}
    plateau = float(np.percentile(fin, hi_pct))
    trough = float(np.percentile(fin, lo_pct))
    return {"plateau": plateau, "trough": trough, "contrast": plateau - trough}


def run_stream(frames: Iterable[np.ndarray], rois: RoiSet,
               measure: Callable[[np.ndarray], dict],
               gate: Optional[LaserGate] = None) -> Iterator[dict]:
    """Drive a per-frame measurement over a stream, pausing while there is nothing to measure.

    ``frames`` yields grabs of ``rois.union()``; ``measure`` takes the pupil region and returns
    a dict (whatever your detector reports). Each result carries ``laser``, ``brightness``, the
    motion energy of every motion region, and — while the gate is shut — a ``status`` of
    ``laser_off`` with no measurement attempted at all.

    The epoch counter increments on every off→on transition, which is the caller's signal to
    forget where the pupil was: between recordings the animal has had minutes to look elsewhere,
    and an anchored search that carries its old position across the gap will start the next
    recording hunting in the wrong place.

    Examples
    --------
    >>> import numpy as np
    >>> rois = RoiSet([Roi("pupil", (0, 0, 20, 20))])
    >>> dark, lit = np.zeros((20, 20), np.uint8), np.full((20, 20), 200, np.uint8)
    >>> out = list(run_stream([dark, dark, lit, lit], rois, lambda c: {"status": "ok"}))
    >>> [r["status"] for r in out]
    ['laser_off', 'laser_off', 'ok', 'ok']
    """
    gate = gate or LaserGate()
    src = rois.brightness_source()
    motion_prev: dict[int, np.ndarray] = {}
    u = rois.union()
    if u is None:
        raise ValueError("no regions to watch")

    for i, big in enumerate(frames):
        cuts = rois.cut_all(big)
        bright = float(src.crop(big, origin=(u[0], u[1])).mean()) if src is not None else 0.0
        lit = gate.update(bright)

        row = {"frame": i, "laser": int(lit), "brightness": bright, "epoch": gate.epoch}
        for k, r in enumerate(rois.items):
            if r.role != "motion":
                continue
            c = cuts[k].astype(np.int16)
            prev = motion_prev.get(k)
            row[f"motion_{k + 1}"] = (float(np.abs(c - prev).mean())
                                      if prev is not None and prev.shape == c.shape else 0.0)
            motion_prev[k] = c

        if not lit:
            row["status"] = "laser_off"
            yield row
            continue

        pupil = rois.of_role("pupil")
        if not pupil:
            row["status"] = "no_pupil_region"
            yield row
            continue
        row.update(measure(pupil[0].crop(big, origin=(u[0], u[1]))))
        row.setdefault("status", "ok")
        yield row
