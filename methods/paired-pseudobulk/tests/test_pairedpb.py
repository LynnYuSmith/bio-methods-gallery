"""The claims this tile makes, as tests."""
import numpy as np
import pytest

from examples.make_sample import REFERENCE_GENE, make_sample
from pairedpb import bh_fdr, median_of_ratios, paired_log2fc, paired_test, top_gene_share


@pytest.fixture(scope="module")
def sample():
    return make_sample(seed=0)


def test_size_factors_track_a_known_library_scaling():
    rng = np.random.default_rng(1)
    profile = np.exp(rng.normal(0, 1.5, 400))
    counts = np.vstack([profile, profile * 2.0, profile * 0.5])
    factors = median_of_ratios(counts)
    assert factors[1] / factors[0] == pytest.approx(2.0, rel=0.05)
    assert factors[2] / factors[0] == pytest.approx(0.5, rel=0.05)


def test_size_factors_ignore_a_few_dominating_genes():
    """A handful of huge genes must not drag the factor — that is the point of the median."""
    rng = np.random.default_rng(2)
    profile = np.exp(rng.normal(0, 1.0, 500))
    skewed = profile.copy()
    skewed[:5] *= 50.0                      # 1 % of genes carrying a large share
    factors = median_of_ratios(np.vstack([profile, skewed]))
    assert factors[1] / factors[0] == pytest.approx(1.0, abs=0.1)


def test_top_gene_share_detects_concentration():
    flat = np.ones((1, 1000))
    peaked = np.concatenate([np.full(50, 100.0), np.ones(950)])[None, :]
    assert top_gene_share(flat)[0] < 10
    assert top_gene_share(peaked)[0] > 80


def test_bh_is_monotone_and_bounded():
    p = np.array([0.001, 0.02, 0.03, 0.5, 0.9])
    q = bh_fdr(p)
    assert np.all(np.diff(q[np.argsort(p)]) >= -1e-12)
    assert q.min() >= 0 and q.max() <= 1


def test_reference_gene_normalisation_biases_the_whole_distribution(sample):
    """The trap: a shifted reference tilts every other gene downward."""
    control, treated, truth = sample
    null = np.abs(truth) <= 0.3
    biased = paired_log2fc(treated, control, normalize="cp10k", reference_gene=REFERENCE_GENE)
    robust = paired_log2fc(treated, control, normalize="median-ratio")
    assert np.median(biased[:, null]) < -0.2      # pushed down
    assert abs(np.median(robust[:, null])) < 0.1  # centred


def test_robust_normalisation_recovers_the_planted_truth(sample):
    control, treated, truth = sample
    res = paired_test(paired_log2fc(treated, control, normalize="median-ratio"))
    real = np.abs(truth) > 0.3
    called = res["significant"]
    assert (called & ~real).sum() == 0            # no false discoveries
    assert (called & real).sum() >= 0.8 * real.sum()
    up, down = (called & (res["median_lfc"] > 0)).sum(), (called & (res["median_lfc"] < 0)).sum()
    assert 0.5 < up / down < 2.0                  # balanced, as planted


def test_reference_gene_normalisation_makes_false_discoveries(sample):
    control, treated, truth = sample
    res = paired_test(paired_log2fc(treated, control, normalize="cp10k",
                                    reference_gene=REFERENCE_GENE))
    real = np.abs(truth) > 0.3
    assert (res["significant"] & ~real).sum() > 10   # the artefact invents genes


def test_rank_test_floor_is_documented_behaviour(sample):
    """At n=8 the signed-rank p cannot beat 2/2**8; BH over many genes then stalls."""
    control, treated, _ = sample
    lfc = paired_log2fc(treated, control, normalize="median-ratio")
    res = paired_test(lfc, test="wilcoxon")
    assert res["p"].min() == pytest.approx(2 / 2 ** 8, rel=1e-6)
    assert res["significant"].sum() < paired_test(lfc, test="t")["significant"].sum()


def test_paired_shapes_must_match():
    with pytest.raises(ValueError):
        paired_log2fc(np.ones((3, 10)), np.ones((4, 10)))
