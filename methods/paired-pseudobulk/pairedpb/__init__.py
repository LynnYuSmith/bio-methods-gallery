"""Within-subject paired pseudobulk differential expression.

The tile's claim in one line: when subjects differ from each other more than the
conditions differ, pair *inside* the subject — and normalise robustly, because
per-10k normalisation turns a shift in composition into a one-sided gene list.
"""
from .core import (
    bh_fdr,
    median_of_ratios,
    paired_log2fc,
    paired_test,
    top_gene_share,
)

__all__ = ["bh_fdr", "median_of_ratios", "paired_log2fc", "paired_test", "top_gene_share"]
