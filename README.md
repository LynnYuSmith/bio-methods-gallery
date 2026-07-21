# Bio-methods gallery

A curated series of small bioinformatics and bio-imaging methods. Each tile is a self-contained
mini-repo or a reproduce-and-extend notebook, readable in an afternoon and runnable in a minute.

It is organised as a gallery of independent tiles. Every tile stands alone, follows one template so the
series reads in one voice, and answers a single question (usually "this method against the established
one, on real data, with a before/after figure").

> Status: private, in progress. Tiles graduate to public one at a time, each after its ownership check
> (below) and a clean pass.

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
