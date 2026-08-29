"""A synthetic paired single-nucleus experiment with a planted truth — and a planted trap.

Eight subjects, each contributing a *control* and a *treated* pseudobulk profile, so the
design is paired inside the subject. Three things are deliberately built in:

* **subject variation** larger than the treatment effect, which is why pairing is needed
  at all (an unpaired test on these data mostly measures who the subject was);
* **a real effect** on a known set of genes, so a method can be scored rather than admired;
* **a "reference" gene that is itself shifted** — the trap. It looks like the obvious
  normaliser (a pan-class marker, highly expressed, present everywhere), but it moves
  more than the typical gene. Subtracting its log-ratio tilts every other gene and
  manufactures a one-sided result. This is not hypothetical: it is what a pan-neuronal
  marker did to a real tangle-vs-neighbour comparison.

Nothing here is lab data; the numbers are drawn from a model.
"""
from __future__ import annotations

import numpy as np

N_SUBJECTS = 8
N_GENES = 1200
N_UP = 50
N_DOWN = 50
REFERENCE_GENE = 0          # the tempting, and misleading, normaliser
REFERENCE_LOG2_SHIFT = 0.35  # it moves ~3-4x more than a typical gene
GLOBAL_LOG2_SHIFT = 0.10     # mild, genuine, whole-library shift
DEPTH = 2_000_000


def make_sample(seed: int = 0):
    """Return ``(control, treated, truth)``.

    ``control``/``treated`` are ``(N_SUBJECTS, N_GENES)`` integer count matrices, row *i*
    of each being the same subject. ``truth`` is the planted per-gene log2 fold change.
    """
    rng = np.random.default_rng(seed)

    # A skewed expression profile: a few genes carry much of the library, as in real data.
    baseline = np.exp(rng.normal(0.0, 1.6, N_GENES))
    baseline[REFERENCE_GENE] = baseline.max() * 1.5      # the reference is highly expressed

    truth = np.zeros(N_GENES)
    picks = rng.choice(np.arange(1, N_GENES), N_UP + N_DOWN, replace=False)
    truth[picks[:N_UP]] = rng.normal(+1.0, 0.25, N_UP)
    truth[picks[N_UP:]] = rng.normal(-1.0, 0.25, N_DOWN)

    control = np.empty((N_SUBJECTS, N_GENES), dtype=np.int64)
    treated = np.empty_like(control)
    for s in range(N_SUBJECTS):
        subject = baseline * np.exp(rng.normal(0.0, 0.9, N_GENES))   # subject >> treatment
        effect = truth.copy()
        effect[REFERENCE_GENE] = REFERENCE_LOG2_SHIFT + rng.normal(0, 0.05)
        treated_profile = subject * 2.0 ** (effect + GLOBAL_LOG2_SHIFT)
        control[s] = rng.multinomial(DEPTH, subject / subject.sum())
        treated[s] = rng.multinomial(DEPTH, treated_profile / treated_profile.sum())
    return control, treated, truth


if __name__ == "__main__":  # pragma: no cover
    c, t, truth = make_sample()
    print(f"control {c.shape}, treated {t.shape}, "
          f"{int((truth > 0).sum())} genes up / {int((truth < 0).sum())} down planted")
