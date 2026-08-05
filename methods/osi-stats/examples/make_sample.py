"""A synthetic population of boutons imaged at 8 drifting-grating directions, few trials.

Most boutons are UNTUNED (flat mean response + noise). A minority are genuinely tuned
(a single von Mises lobe — direction selective). Each bouton has only a handful of trials
per direction, which is the regime where the OSI point estimate is positively biased: an
untuned bouton still scores OSI > 0 by chance.

Ground truth (which boutons are really tuned) is returned so the two calls can be scored.
"""
import numpy as np

ORIENTATIONS = np.arange(0, 360, 45).astype(float)   # 8 directions


def make_population(n_boutons: int = 200, frac_tuned: float = 0.15, n_trials: int = 10,
                    noise: float = 1.0, seed: int = 0):
    """Return ``(mean_by_bouton, trials_by_bouton, truth, orientations)``.

    ``mean_by_bouton`` is ``(n_boutons, 8)``; ``trials_by_bouton`` is
    ``(n_boutons, 8, n_trials)``; ``truth`` is a bool array (True = genuinely tuned).
    """
    rng = np.random.RandomState(seed)
    ori = ORIENTATIONS
    n_ori = len(ori)
    n_tuned = int(round(n_boutons * frac_tuned))
    truth = np.zeros(n_boutons, dtype=bool)
    truth[:n_tuned] = True
    rng.shuffle(truth)

    trials = np.empty((n_boutons, n_ori, n_trials))
    for b in range(n_boutons):
        if truth[b]:
            pref = rng.uniform(0, 360)
            kappa = rng.uniform(3.0, 6.0)               # tuning sharpness
            amp = rng.uniform(5.0, 9.0)                 # signal well above noise
            d = np.deg2rad(ori - pref)
            profile = amp * np.exp(kappa * (np.cos(d) - 1.0))   # single lobe
        else:
            profile = np.zeros(n_ori)                   # flat: no tuning
        # Responses are baseline-subtracted ΔF/F scores: ~0 when there is no response, so
        # there is NO uniform positive pedestal (a pedestal would dilute the Rayleigh
        # resultant and drag OSI down — it is not physical here).
        trials[b] = profile[:, None] + rng.normal(0, noise, (n_ori, n_trials))

    mean_by_bouton = trials.mean(axis=2)
    return mean_by_bouton, trials, truth, ori


if __name__ == "__main__":
    M, T, truth, ori = make_population()
    print(f"{M.shape[0]} boutons, {M.shape[1]} directions, {T.shape[2]} trials/dir; "
          f"{truth.sum()} genuinely tuned")
