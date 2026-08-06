# Bio-methods gallery

A curated series of small bioinformatics and bio-imaging methods. Each tile is a self-contained
mini-repo or a reproduce-and-extend notebook, readable in an afternoon and runnable in a minute.

It is organised as a gallery of independent tiles. Every tile stands alone, follows one template so the
series reads in one voice, and answers a single question (usually "this method against the established
one, on real data, with a before/after figure").

> Status: private, in progress. Tiles graduate to public one at a time, each after its ownership check
> (below) and a clean pass.

## Built so far

| tile | what it shows |
|---|---|
| [master-served-report](methods/master-served-report) | one HDF5 experiment file served live over a small REST API; the browser report reads everything from it |
| [bouton-detection](methods/bouton-detection) | boutons detected by activity, not brightness; the size window is read from the recording's own active regions |
| [group-motion-correction](methods/group-motion-correction) | several recordings of one field of view registered to a shared reference, so one ROI fits them all |
| [cross-session-registration](methods/cross-session-registration) | the same field of view matched across days in 3-D on a vesselness fingerprint of the axon arbor, recovering the z-offset that xy-only registration drops (0/25 → 25/25 boutons matched) |
| [pupil-tracking](methods/pupil-tracking) | a per-frame pupil detector run across a video with temporal consistency, so blinks and distractors don't break the pupil-size trace |
| [dff-baseline](methods/dff-baseline) | a rolling median baseline, left unclipped, so ΔF/F sits symmetric around zero instead of biased up by a lower-envelope |
| [osi-stats](methods/osi-stats) | orientation selectivity called with a shuffle test and population FDR, so a bare OSI threshold's positive-bias false positives are controlled |
| [trace-qc](methods/trace-qc) | two per-trace quality gates on their proper representations: SNR (MAD-based noise floor) graded on ΔF/F, and a photobleaching fit on the raw fluorescence |

![group motion correction: a shared reference aligns the recordings](methods/group-motion-correction/figures/before_after.png)

## Companion tools (separate repos)

Two standalone tools that share the gallery's spirit — a method, a synthetic demo, tests — but
are full applications in their own repos rather than in-tree tiles. They form a closed loop: one
plays the stimulus and writes its protocol, the other decodes that protocol back out of the
recording.

| tool | what it does |
|---|---|
| [stimulus-runner](https://github.com/LynnYuSmith/stimulus-runner) | a browser (WebGL) drifting/static grating presenter — seamless grey/black ↔ grating, a sequence of blocks, RED corner pulse markers, and a played-protocol export that overlays onto the recording |
| [stimulus-aligner](https://github.com/LynnYuSmith/stimulus-aligner) | decodes the recording's photodiode pulse markers and aligns that played protocol onto the frame-exact timeline (which block, and when it truly started) |

## Two tile types

(A) Method mini-repo (`methods/<name>/`). One API, one runnable example, one before/after figure, a
test suite, and a README carrying the logic, the paper it compares against, and a license. The bar for
a tile: a stranger clones it, runs the example, and reads off the reason it beats the obvious baseline
from one figure.

(B) Showcase notebook (`notebooks/<name>.ipynb`). A «красива лабораторка»: a published study reproduced
cleanly, then carried one step past a question the paper left open. It reads like a lab notebook and
closes on a result the paper did not report.

Both share the look defined in `_template/`.

## The ownership gate (read before any tile goes public)

Several methods here originate in work owned by Eberhard Karls Universität Tübingen and the Garaschuk
lab. Each is sorted before publication:

| tier | meaning | action |
|---|---|---|
| hers and novel | her own idea, unpublished elsewhere | open with attribution |
| wrapper on open tools | a thin layer over Suite2p, CaImAn, scanpy (already open) | cite, keep the wrapper thin |
| lab IP | a lab method or an unpublished result | explicit consent from the lab first |

One conscious step per tile.

## Faithful to the pipeline (sync)

Where a tile shows a real lab-pipeline method, its core maths is an **independent copy** of the actual
pipeline function — not a parallel reimplementation that drifts and rots (a divergent copy is how a
standalone tool once shipped a bug the live code never had). `_sync/` lifts the named functions out of
the private pipeline, **de-identifies** them (strips recording IDs / names / paths, with a fail-loud
guard), stamps provenance (source + commit + date), and writes each tile's generated `_synced.py`. A
fix flows one way: fix the pipeline, re-run `python _sync/sync.py`, and any drift shows in the tile's
diff. Not git submodules — that would embed the private repo and defeat de-identification. Some tiles
have no lab-owned function to copy (the workflow *is* the tile's contribution, or the engine is
third-party like Suite2p); those stay tile-original. Details + the per-tile table: [`_sync/README.md`](_sync/README.md).

## Index

`ROADMAP.md` lists the planned tiles (a calcium set, an RNA-seq set, a proteomics set), each with its
ownership tier and the established method it is benchmarked against.

## Make a new tile

```bash
cp -r _template/methodname methods/<your_method>
# rename methodname/, then fill in the README, the code, one example, one figure, the tests
```

## Shared style

Every tile draws through `gallery_style` (a quiet white-ground look built on Fabio Crameri'''s
scientific colour maps): a light-grey grid, a darker-grey zero line, muted categorical colours, and
axis labels in the journal form (the quantity, a comma, the unit: `time, s` and `ΔF/F, a.u.`, never
`time (s)`). Install it into a tile'''s environment with `pip install -e ../../gallery_style`.
