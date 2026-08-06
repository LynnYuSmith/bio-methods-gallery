# trace-trustworthiness

After 2-D motion correction, is a bouton's trace still measuring the **same bouton** — or did
it drift in **x, y** (mixing in neighbours) or in **z** (leaving the focal plane and reading as
falsely quiet)? Two checks that a corrected ΔF/F trace alone can't make.

**Ownership tier:** hers / wrapper (the xy tracking reuses the pipeline's registration engine;
the z-drift detector — resting-fluorescence decline versus the field — is the contribution).

![three boutons after motion correction: one trustworthy, one with residual xy motion, one z-drifting so its trace reads as falsely silent](figures/before_after.png)

## The idea

Suite2p (and 2-D motion correction generally) fixes **x** and **y** but not **z**. Two failure
modes survive it, and both make a trace lie:

- **Residual xy motion.** The ROI keeps sliding across the sensor, so the trace mixes in
  neighbouring pixels. Detected by **tracking the bouton's patch over time**: split the movie
  into time bins and register each bin's mean patch to the first with the pipeline's
  `register_fov_xy` (phase cross-correlation). A trustworthy bouton's patch barely moves; a
  drifting one accumulates a sub-pixel displacement bin after bin.

- **z-drift.** The bouton drifts out of the focal plane, so its brightness falls and the trace
  reads as **going quiet even though the cell never changed its firing** — and a 2-D pipeline
  cannot see it. It is separated from FOV-wide **photobleaching** by comparing the bouton's own
  resting-fluorescence decline to the **median decline across the field**: a bouton that dims
  *faster than the field*, while its patch stays put, is z-drifting — a **false silence**. The
  z-drift detector is this tile's own contribution.

The order matters: check the patch first (residual motion explains a resting-level drop when the
bouton slides out of its ROI), then, for a bouton that has *not* moved, ask whether it dimmed
faster than the field. On synthetic data with a known problem per bouton — *stable* (steady),
*xy_drift* (slides ~5 px), *z_drift* (dims to a few percent while the field bleaches ~20 %) —
each gets its true verdict, and the z-drifting bouton's apparent silence is correctly called an
artifact, not a real drop in activity.

## Use

```python
from tracetrust import assess

# stack: (T, H, W) motion-corrected movie; rois: {name: (cy, cx, half_box)}
report = assess(stack, rois)
report["MyBouton"]["verdict"]              # 'trustworthy' | 'residual-motion' | 'z-drift'
report["MyBouton"]["residual_shift_px"]    # tracked xy displacement
report["MyBouton"]["zdrift_excess"]        # resting-F decline beyond the FOV median
```

## Run the example

```bash
python -m venv .venv && source .venv/bin/activate    # Python 3.10+
pip install -e . && pip install pytest matplotlib && pip install -e ../../gallery_style
python examples/demo.py         # writes figures/before_after.png
pytest
```

## Limitations

The z-drift check needs several ROIs to estimate the FOV-wide bleaching (the median decline);
with one ROI there is nothing to compare against. It assumes photobleaching is roughly uniform
across the field. Residual-motion tracking needs the bouton to stay partly inside its ROI box
(a bouton that slides fully out becomes untrackable — which is itself a red flag). z is inferred
from brightness, not measured optically; a true z-stack (see the `cross-session-registration`
tile) resolves z directly.

## License

See `LICENSE`.
