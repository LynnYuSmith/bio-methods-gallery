"""OSI with a significance test and population FDR.

The Orientation Selectivity Index (OSI) is a point estimate, and with a modest trial count
and real noise it is **positively biased**: an untuned neuron still scores OSI > 0 by
chance, so a bare threshold (OSI > 0.3) flags untuned cells as tuned. Do that across a
whole population and the false positives pile up.

The rigorous call keeps the OSI as a descriptive number but decides tuning with a
**shuffle test** (z-scored against OSI's own bias null) and then corrects for testing
every neuron in the population with **Benjamini-Hochberg FDR**. What survives is tuned at a
controlled false-discovery rate.

* ``selectivity.osi`` — the OSI point estimate (folded to orientation space, negatives
  rectified), reproduced from the pipeline.
* ``significance.shuffle_test_osi`` — z-scored trial-shuffle test on OSI.
* ``significance.rayleigh_test`` — a non-uniformity test (Fisher 1993 closed form; sample
  size = number of sampled directions, not Kish's effective n), provided as a utility.
* ``significance.benjamini_hochberg`` — FDR-adjusted q-values across the population.
* ``significance.classify_population`` — naive-threshold vs shuffle-test + FDR.
"""
from .selectivity import osi
from .significance import (
    benjamini_hochberg,
    bootstrap_osi_ci,
    classify_population,
    rayleigh_test,
    shuffle_test_osi,
)

__all__ = [
    "osi",
    "shuffle_test_osi",
    "rayleigh_test",
    "benjamini_hochberg",
    "bootstrap_osi_ci",
    "classify_population",
]
