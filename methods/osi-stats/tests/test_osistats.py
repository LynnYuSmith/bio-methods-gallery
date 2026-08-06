import numpy as np

from make_sample import make_population
from osistats import (
    benjamini_hochberg,
    classify_population,
    osi,
    rayleigh_test,
)


def test_osi_range_and_tuned_higher():
    M, _T, truth, ori = make_population(seed=0)
    osis = np.array([osi(row, ori) for row in M])
    finite = osis[np.isfinite(osis)]
    assert finite.min() >= 0.0 and finite.max() <= 1.0
    # genuinely tuned boutons have higher OSI on average than untuned
    assert np.nanmean(osis[truth]) > np.nanmean(osis[~truth])


def test_rayleigh_flat_is_not_significant():
    # a perfectly flat profile → uniform → p near 1
    ori = np.arange(0, 360, 45).astype(float)
    _z, p = rayleigh_test(ori, weights=np.ones(len(ori)))
    assert p > 0.5


def test_benjamini_hochberg_bounds_and_monotone():
    p = np.array([0.001, 0.01, 0.02, 0.2, 0.5, 0.9])
    q = benjamini_hochberg(p)
    assert np.all(q >= p - 1e-12)          # q-values are adjusted upward
    assert np.all(np.diff(q[np.argsort(p)]) >= -1e-12)   # monotone in p-order
    assert np.all((q >= 0) & (q <= 1))


def test_benjamini_hochberg_handles_nan():
    q = benjamini_hochberg([0.01, np.nan, 0.5])
    assert np.isnan(q[1]) and np.isfinite(q[0]) and np.isfinite(q[2])


def test_honest_has_fewer_false_positives_than_naive():
    _M, T, truth, ori = make_population(seed=0)
    r = classify_population(T, ori, osi_thr=0.33, alpha=0.05, n_shuffle=300)
    fp_naive = np.sum(r["naive"] & ~truth)
    fp_honest = np.sum(r["honest"] & ~truth)
    assert fp_naive > 0                    # the bias really does flag untuned boutons
    assert fp_honest < fp_naive            # FDR controls them
    # and the honest call still recovers most of the genuinely tuned boutons
    assert np.sum(r["honest"] & truth) >= 0.5 * truth.sum()


def test_fdr_removes_false_positives_a_raw_threshold_would_keep():
    # A large PURE-NULL population: an UNCORRECTED p < alpha flags several untuned boutons by
    # chance; Benjamini-Hochberg across the family must remove them. This exercises the headline
    # "+FDR" step — on the clean demo data the shuffle test alone already yields 0 FP, so FDR
    # never bites there and a "no correction" mutation passes unnoticed (adversarial finding).
    rng = np.random.RandomState(3)
    ori = np.arange(0, 360, 45).astype(float)
    T = rng.normal(0.0, 1.0, (200, 8, 6))            # every bouton untuned (pure noise)
    r = classify_population(T, ori, alpha=0.05, n_shuffle=500, seed=3)
    raw_fp = int(np.sum(r["pval"] < 0.05))           # what an uncorrected threshold would flag
    bh_fp = int(np.sum(r["honest"]))                 # what BH-FDR flags
    assert raw_fp >= 2, raw_fp                        # uncorrected p DOES flag untuned by chance
    assert bh_fp == 0, bh_fp                          # FDR removes them all on a pure-null family
    assert bh_fp < raw_fp                             # ...so the FDR step is demonstrably not inert
