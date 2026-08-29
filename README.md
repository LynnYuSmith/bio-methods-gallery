# Bio-methods gallery

[![tests](https://github.com/LynnYuSmith/bio-methods-gallery/actions/workflows/tests.yml/badge.svg)](https://github.com/LynnYuSmith/bio-methods-gallery/actions/workflows/tests.yml)

Small, self-contained bioinformatics and bio-imaging methods. Each tile stands alone, runs in a
minute, and answers one question — *this method against the established one, on a synthetic example
that ships with it, in one before/after figure*.

Every tile carries its own generator (`examples/make_sample.py`), so nothing here needs lab data:
clone it, run it, and the figure rebuilds itself.

> Open and in progress — MIT, copyright Universität Tübingen. Please cite it if it helps your work
> ([CITATION.cff](CITATION.cff)).

## Methods

| tile | what it shows |
|---|---|
| [master-served-report](methods/master-served-report) | one HDF5 experiment file served live over a small REST API; the report reads everything from it |
| [bouton-detection](methods/bouton-detection) | boutons detected by activity, not brightness; the size window comes from the recording's own active regions |
| [group-motion-correction](methods/group-motion-correction) | repeat recordings of one FOV registered to a shared reference, so one ROI fits them all |
| [cross-session-registration](methods/cross-session-registration) | the same FOV matched across days in 3-D on a vesselness fingerprint, recovering the z-offset xy-only registration drops (0/25 → 25/25 boutons matched) |
| [pupil-tracking](methods/pupil-tracking) | a per-frame pupil detector run with temporal consistency, so blinks and distractors don't break the pupil-size trace |
| [dff-baseline](methods/dff-baseline) | a rolling **median** baseline, left unclipped, so ΔF/F sits symmetric around zero instead of biased up |
| [osi-stats](methods/osi-stats) | orientation selectivity called with a shuffle test + population FDR, not a bare OSI threshold |
| [trace-qc](methods/trace-qc) | two per-trace gates on their proper representations: SNR (MAD noise floor) on ΔF/F, photobleaching fit on raw F |
| [trace-trustworthiness](methods/trace-trustworthiness) | after motion correction — per-ROI residual motion during running bouts (x, y and z), flagging each bouton's residual shift and catching boutons pushed out of their ROI, where the trace reads background |
| [mesc-reader](methods/mesc-reader) | read a Femtonics .mesc (it's HDF5) → TIFF or HDF5, applying each channel's PMT-offset display conversion by default (loudly; −786 green / −1170 red), with raw/manual overrides and a CLI |
| [mesc-motion-correct](methods/mesc-motion-correct) | group motion correction — one shared reference from the first unit registers a whole train of .mesc repeats onto the same grid; offset and pixel size read from the file; .mesc in → .mesc out |

![a shared reference aligns repeat recordings](methods/group-motion-correction/figures/before_after.png)

## Companion tools

Standalone apps in their own repos, same spirit (method + synthetic demo + tests). Together they form a
**closed loop on the two-photon rig**: one plays the stimulus and writes its protocol, one decodes that
protocol back out of the recording, and one reads the mouse's behaviour live and gates the stimulus on it.

| tool | what it does |
|---|---|
| [stimulus-runner](https://github.com/LynnYuSmith/stimulus-runner) | browser (WebGL) grating presenter — seamless grey/black ↔ grating, block sequence, RED corner pulse markers, played-protocol export |
| [stimulus-aligner](https://github.com/LynnYuSmith/stimulus-aligner) | decodes the photodiode pulse markers and aligns that protocol onto the frame-exact timeline |
| [behavior-trigger](https://github.com/LynnYuSmith/behavior-trigger) | reads running/stationary live from the camera (frame-diff + hysteresis), writes frame+motion into LabChart for cross-modal alignment, and gates the stimulus (pause on run, resume on settle) — a sense→decide→act loop with a measured 67 ms onset latency |

## Ownership and attribution

These methods come out of work at Eberhard Karls Universität Tübingen (Garaschuk lab), which holds the
copyright; they are released open under [MIT](LICENSE) with a request to cite.

- **Thin wrappers stay thin, and name what they wrap** — Suite2p, CaImAn, scikit-image, scanpy do the
  heavy lifting where a tile says so; the contribution is the workflow around them.
- **Borrowed pieces are credited** — the per-frame pupil detector behind `pupil-tracking` is Sonja
  Nevelchuk's, reimplemented clean-room with permission; the tracking layer is the contribution.
- **Unpublished science is not here.** A method whose scientific claim is still unpublished waits for
  the paper; the gallery ships methods, and each demo runs on synthetic data, never on lab recordings.

## Sync — faithful to the pipeline

Where a tile shows a real pipeline method, its core maths is an **independent copy** of the actual
function, not a reimplementation that drifts. `_sync/` lifts the named functions out of the private
pipeline, de-identifies them (IDs / names / paths, fail-loud guard), stamps provenance, and writes each
tile's `_synced.py`. Fix flows one way: fix the pipeline → `python _sync/sync.py` → the copy updates and
drift shows in the diff. Not submodules (that would embed the private repo). Tiles with no lab-owned
function to copy stay tile-original. See [`_sync/README.md`](_sync/README.md).

## Structure

- A tile is `methods/<name>/`: one API, one example, one before/after figure, tests, a README, a license.
- `notebooks/<name>.ipynb` — a reproduce-and-extend showcase (a published study, one step past what it reported).
- `ROADMAP.md` — planned tiles (calcium, RNA-seq, proteomics sets), each with its tier and benchmark.
- New tile: `cp -r _template/methodname methods/<name>`, then fill it in.

Every tile draws through `gallery_style` (Crameri colour maps, quiet white ground, journal axis labels
`quantity, unit`): `pip install -e ../../gallery_style`.

## Running the tests

Each tile is a standalone project, so they are run one at a time (their test modules share names,
which a single root-level `pytest` run cannot import together):

```bash
./run_tests.sh              # every tile + the sync guard
./run_tests.sh dff-baseline # one tile
```

## License

Open source under the [MIT License](LICENSE) — free to read, run, modify and build on.
Copyright (C) 2026 Eberhard Karls Universität Tübingen / [Polina Yu Koval].

**Please cite it.** If a method here contributes to work you publish or present, cite the
repository — the entry is in [CITATION.cff](CITATION.cff) (GitHub's "Cite this repository"
button reads it). The licence also carries terms of use regarding russia's war against Ukraine.
