# `_sync/` — gallery tiles as independent copies of the lab pipeline

The gallery tiles are **independent copies** of the real pipeline functions, not parallel
reimplementations. A divergent copy rots: it drifts from the live code and can end up with bugs the
pipeline never had (exactly how a standalone tool once shipped an off-by-one the live decoder didn't
have). So the rule is: **fix the method in the pipeline, then re-run the sync** — the fix flows one
way, and any drift shows up in the tile's git diff.

Not git submodules, deliberately: the pipeline is private (unpublished science, lab IP, recording
IDs) and the gallery is meant to be publishable. A submodule would embed the whole private repo and
defeat de-identification. Instead we lift *named functions*, de-identify them, and stamp provenance.

## How it works

- **`manifest.py`** — per tile: which pipeline source file + which symbols to lift, the import
  header those symbols need, and the destination `_synced.py`.
- **`sync.py`** — for each symbol: extract it by AST (exact named def), de-identify, stamp a
  provenance header (source path + pipeline commit + date), write `<tile>/<pkg>/_synced.py`.
- **`deident.py`** — rewrites lab-internal references (recording IDs like `cm0xx`, personal names,
  `/Users/…` paths) and then a **fail-loud guard** re-scans and raises if any forbidden token
  survives, so a missed pattern fails the sync instead of leaking silently.

Generated `_synced.py` files carry `DO NOT EDIT BY HAND`. Each tile's own module wraps them with a
small named API; the demo, tests, README, and synthetic sample stay tile-authored.

## Use

```bash
python _sync/sync.py                 # regenerate every tile from the pipeline
python _sync/sync.py --tile osi-stats
python _sync/sync.py --check         # verify no drift; exit 1 if a tile is stale (CI)
python _sync/sync.py --repo /path/to/CalciumPipelineLib
```

Point it at the pipeline with `--repo` or `PIPELINE_REPO` (default in `manifest.PIPELINE_DEFAULT`).

## Which tiles are synced copies vs the tile's own

| tile | synced from the pipeline | the tile's own contribution |
|------|--------------------------|-----------------------------|
| **dff-baseline** | `rolling_baseline`, `maximin_baseline` | median-vs-envelope framing, demo |
| **osi-stats** | `calculate_osi`, `rayleigh_test` | the population shuffle + FDR call |
| **group-motion-correction** | `register_fov_xy` (+ prep, peak-corr) — incl. the SUBTRACT sign convention | the shared-reference group workflow |
| **bouton-detection** | *(none — no lab twin)* | the whole activity-map + data-driven-window workflow; real engine is Suite2p |
| **pupil-tracking** | *(none — no lab-**owned** twin)* | Sonja Nevelchuk's detector, clean-room reimplemented with permission; Lynn's tracking tool |
| **master-served-report** | *(not yet)* | — |

Some methods have no lab-authored function to copy (the workflow *is* the tile's contribution, or the
real engine is third-party). Those stay tile-original and are not forced into a fake `_synced.py`.
The pipeline *does* contain a same-family pupil implementation, but it is not lab-**owned** (the detector
is external, reimplemented with permission), so there is no lab-owned function to sync — "no twin" here
means "no lab-owned twin", not "no analog exists".

**De-identification boundary.** The fail-loud guard (`deident.py`) runs only over **synced code**
(`_synced.py`). Hand-authored files — READMEs, LICENSEs, docstrings in tile-original modules — carry
names by design (pseudonymous author, consented attribution) and are **not** machine-scanned, so a
non-consented name there would not be caught automatically. Review those by hand before publishing.
