"""Paired pseudobulk DE with the two controls that decide the answer.

Pseudobulk first (sum counts per sample, subject as the unit) — per-cell tests treat
nuclei from one subject as independent and inflate significance. Then two things that
are easy to skip and change the result:

1. **Composition.** Per-10k (CPM/CP10K) normalisation assumes the total is comparable.
   When one condition's counts concentrate into fewer genes, every other gene is pushed
   down mechanically and the DE list comes out one-sided. :func:`top_gene_share` measures
   that concentration; :func:`median_of_ratios` normalises without assuming it away.
2. **A shared baseline shift.** If both conditions differ in the proportion of the cell
   class you care about, every marker of that class moves together. Subtracting a
   reference gene's own log-ratio (a pan-class marker) expresses each gene *relative to*
   that shift, so what remains is composition within the class rather than of it.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import ttest_rel, wilcoxon

_EPS = 1e-6


def top_gene_share(counts: np.ndarray, k: int = 50) -> np.ndarray:
    """Fraction (%) of a sample's counts held by its top ``k`` genes.

    The compositional diagnostic. Run it on both conditions BEFORE trusting a one-sided
    DE result: a gap of several points means per-10k normalisation is not comparing like
    with like, and the smaller-share condition will look globally "up".

    ``counts`` is (samples × genes). Returns one percentage per sample.
    """
    counts = np.atleast_2d(np.asarray(counts, dtype=float))
    ordered = np.sort(counts, axis=1)[:, ::-1]
    totals = counts.sum(axis=1)
    totals[totals == 0] = np.nan
    return 100.0 * ordered[:, :k].sum(axis=1) / totals


def median_of_ratios(counts: np.ndarray, reference: np.ndarray | None = None) -> np.ndarray:
    """DESeq2-style size factors: the median per-gene ratio to a reference profile.

    Robust to a minority of genes carrying a large share of the counts, which is exactly
    the case per-10k gets wrong. Genes that are zero in the reference are ignored.
    Returns one factor per sample (multiply-divide space, not log).
    """
    counts = np.atleast_2d(np.asarray(counts, dtype=float))
    if reference is None:                      # geometric mean across samples
        with np.errstate(divide="ignore"):
            log_ref = np.nanmean(np.log(np.where(counts > 0, counts, np.nan)), axis=0)
        reference = np.exp(log_ref)
    usable = np.isfinite(reference) & (reference > 0)
    if not usable.any():
        return np.ones(counts.shape[0])
    ratios = counts[:, usable] / reference[usable]
    ratios[~np.isfinite(ratios) | (ratios <= 0)] = np.nan
    factors = np.nanmedian(ratios, axis=1)
    factors[~np.isfinite(factors) | (factors <= 0)] = 1.0
    return factors


def paired_log2fc(treat: np.ndarray, control: np.ndarray, *,
                  normalize: str = "median-ratio",
                  reference_gene: int | None = None) -> np.ndarray:
    """Per-subject log2 fold change, treatment vs its own control.

    ``treat``/``control`` are (subjects × genes) pseudobulk counts, row *i* of each being
    the SAME subject. ``normalize`` is ``"median-ratio"`` (default) or ``"cp10k"`` — the
    naive one, kept so the difference can be shown rather than asserted.
    ``reference_gene`` subtracts that gene's own log-ratio per subject (see module docstring).
    """
    treat = np.atleast_2d(np.asarray(treat, dtype=float))
    control = np.atleast_2d(np.asarray(control, dtype=float))
    if treat.shape != control.shape:
        raise ValueError(f"paired arrays must match: {treat.shape} vs {control.shape}")

    if normalize == "cp10k":
        t = 1e4 * treat / np.maximum(treat.sum(1, keepdims=True), 1)
        c = 1e4 * control / np.maximum(control.sum(1, keepdims=True), 1)
    elif normalize == "median-ratio":
        stacked = np.vstack([control, treat])
        factors = median_of_ratios(stacked)
        c = control / factors[: len(control), None]
        t = treat / factors[len(control):, None]
    else:
        raise ValueError("normalize must be 'median-ratio' or 'cp10k'")

    lfc = np.log2((t + _EPS) / (c + _EPS))
    if reference_gene is not None:
        lfc = lfc - lfc[:, [reference_gene]]
    return lfc


def bh_fdr(pvalues: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (monotone, clipped at 1)."""
    p = np.asarray(pvalues, dtype=float)
    n = p.size
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty_like(ranked)
    q[order] = np.clip(ranked, 0, 1)
    return q


def paired_test(lfc: np.ndarray, *, test: str = "t",
                min_abs_lfc: float = 0.5, alpha: float = 0.05):
    """Per-gene paired test across subjects, then BH.

    ``test="t"`` (default) is a paired t-test on the log-ratios; ``test="wilcoxon"`` is the
    signed-rank test.

    **Why the default is parametric at small n.** The signed-rank p-value cannot go below
    ``2 / 2**n`` — 0.0078 at n=8 — so after BH over *G* genes the best attainable q is
    ``0.0078 * G / rank``. With 1,200 genes nothing clears q<0.05 until ~190 genes sit
    exactly at the floor, and a *biased* analysis reaches that count more easily than an
    unbiased one: the rank test can reward the artefact it should expose. The t-test on
    log-ratios keeps a continuous p-value and stays usable at n=8. Use the rank test when
    n is larger or the log-ratios are visibly non-normal, and read the direction count
    (``n_up``) alongside either.

    Returns a dict of arrays: ``median_lfc``, ``n_up``, ``p``, ``q``, ``significant``.
    """
    lfc = np.atleast_2d(np.asarray(lfc, dtype=float))
    n_subjects, n_genes = lfc.shape
    median = np.median(lfc, axis=0)
    n_up = (lfc > 0).sum(axis=0)
    if test == "t":
        with np.errstate(invalid="ignore"):
            p = ttest_rel(lfc, np.zeros_like(lfc), axis=0).pvalue
        p = np.where(np.isfinite(p), p, 1.0)
    elif test == "wilcoxon":
        p = np.ones(n_genes)
        for g in range(n_genes):
            column = lfc[:, g]
            if np.allclose(column, 0):
                continue
            p[g] = wilcoxon(column).pvalue
    else:
        raise ValueError("test must be 't' or 'wilcoxon'")
    q = bh_fdr(p)
    return {"median_lfc": median, "n_up": n_up, "p": p, "q": q,
            "significant": (q < alpha) & (np.abs(median) > min_abs_lfc),
            "n_subjects": n_subjects}
