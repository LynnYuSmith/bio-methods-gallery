# pupil-tracking

Measure the pupil by fitting its **border**, not by counting its bright pixels — and turn that
per-frame measurement into one honest trace, with gaps where there was nothing to measure.

![the blob merges with lid glare and reads it as a dilation; the border does not](figures/before_after.png)

## The problem with the obvious approach

Under coaxial infrared illumination the pupil retro-reflects: it is the brightest structure in
the eye, a saturated plateau with a sharp fall into the darker iris. The obvious measurement is
to threshold the bright pixels, take the largest bright region and report its equivalent radius
`r = sqrt(area / pi)`.

That measures **how many pixels are bright**, and lid glare is also bright. Where glare covers
part of the pupil's border the two become one bright region, the equivalent radius grows
smoothly, and the error looks exactly like a dilation — no warning sign, nothing to catch it
downstream.

The two methods fail differently, and that is the argument. On the synthetic clip in
`examples/`, on the frames where the glare band lies across the border, the blob answers every
single frame and is wrong by up to **5.3 px**, while the border method **refuses** them: it
cannot see the occluded arc, so it says so. Wrong-and-confident against declining to answer.

## What this measures instead

The border, ray by ray:

1. **Anchor a centre** in the bright plateau — from the previous frame when tracking, so a
   brighter structure elsewhere in the window cannot capture the measurement.
2. **Read the radial profile** in 1-px annuli around it: the plateau is the pupil's own
   brightness, the trough the iris behind its border. Their difference is the contrast, and
   below a floor there is no border to find.
3. **Cast 48 rays** and find where each crosses the half-drop level, to sub-pixel precision.
4. **Keep a ray only if its darkness held** for a few micrometres past the crossing. A ray
   grazing an eyelash or the rim of a glare band dips below the level and climbs straight back
   out; a border does not.
5. **Discard a crossing whose hold cannot be verified inside the given rectangle.** A ray aimed
   at a dark corner of a tight eye window leaves the image a sample or two after it drops, and
   forty-eight such rays fit a circle the size of the window to a fraction of a pixel — a clean
   fit to nothing. This is the most dangerous failure of the method and it costs one line to
   close.
6. **Fit a least-squares circle** through the confirmed crossings, and judge it by its
   **residual and visible arc** rather than by how many points it has. A real border gives a
   sharp contour from few points; an over-reading fit scatters. Point count and residual
   correlate only weakly, so the residual is the discriminator.

A frame that fails those guards is **refused**, with the reason attached. A refusal is
information: a blink has no pupil, and reporting a number for it corrupts every average
downstream.

## The temporal layer

`track.py` supplies the memory the per-frame measurement deliberately lacks:

* **anchoring** — each frame's search starts from the last accepted centre;
* **re-acquisition** — after a run of refusals the anchor is stale, so the search is released
  to the whole frame again;
* **short gaps interpolated, long ones not** — a three-frame blink between solid measurements
  can be bridged honestly; a hundred-frame loss cannot;
* **transient jumps refused** — a pupil dilates smoothly, so a diameter that leaps and returns
  within a couple of frames is the fit moving, not the eye. Those frames are dropped, not
  smoothed: smoothing hides the disagreement that tells you the measurement went wrong.

Nothing smooths the surviving samples. A caller who wants a smooth trace can smooth it
knowingly.

## Calibration

The half-drop border sits slightly inside the disc a human outlines, by a constant that depends
on the optics rather than on the pupil — an **additive** offset, not a scale factor. Measure it
once per rig against a handful of hand-drawn references and set `EDGE_OFFSET`. Do not tune the
level to make the constant small: that improves the constant and worsens the agreement, which
is the trap of calibrating against your own method.

## Use

```python
from pupiltrack import track_pupil, detect_border

r = detect_border(frame)              # one frame: radius, residual, arc, contrast, status
out = track_pupil(frames)             # frames: (n, H, W), an eye-ROI stack
radius = out["radius"]                # per-frame radius, NaN where nothing was measurable
status = out["status"]                # "measured" / "interpolated" / the refusal's reason
```

## Run the example

```bash
python -m venv .venv && source .venv/bin/activate    # Python 3.10+
pip install numpy scipy matplotlib pytest
python examples/demo.py --figure
python -m pytest tests/ -q
```

The demo prints, on the synthetic clip:

```
brightest blob       median |error|   1.64 px   on 140/140 frames
border, per frame     median |error|   0.40 px   on 119/140 frames
border + tracking     median |error|   0.40 px   on 120/140 frames

on the 14 glare frames (blinks excluded):
  brightest blob      bias +2.61 px, worst 5.33

blinks: the blob reports a number on 4 of 4; the border refuses 4 of 4
```

Read the frame counts as part of the result. The blob measures 140 of 140 and is four times
less accurate; the border measures 120 and is right to 0.4 px on those. The twenty it declines
are the blinks and the frames whose border the glare covers — and a trace with honest gaps is
worth more than a full one you cannot check.

Everything here runs on synthetic frames generated by `examples/make_sample.py` — no recorded
data is included or required.

## Note on an earlier version

An earlier version of this tile demonstrated the temporal layer on a **dark-pupil** blob
detector (Sonja Nevelchuk's algorithm, reimplemented clean-room with her permission). That
detector belongs to a different imaging regime — a dark pupil against a lighter iris — and is
no longer part of the tile. What is shown now is the bright-pupil border fit and its temporal
layer.
