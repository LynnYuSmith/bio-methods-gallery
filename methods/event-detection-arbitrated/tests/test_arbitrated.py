"""What the tile claims, as tests: the noise scale decides, and the null population judges."""
import numpy as np
import pytest

from make_sample import calcium_kernel, denoise_ar1, make_sample
from arbitrated import (VARIANTS, arbitrate, calm_window_baseline, detect,
                        detect_events_arbitrated, false_positive_rate, noise_ratio,
                        noise_sigma_negative_tail, population_rate)

FPS = 30.0


@pytest.fixture(scope="module")
def sample():
    return make_sample(seed=0)


def test_denoising_shrinks_the_noise_in_both_populations(sample):
    """The premise: a denoised trace's own sigma no longer describes the recording's noise."""
    r = noise_ratio(sample)
    assert r["bouton"] > 1.5
    assert r["background"] > 1.5
    # and it hides MORE of the noise where there is more of it to hide
    assert r["background"] > r["bouton"]


def test_the_bar_from_the_measured_trace_is_the_higher_one(sample):
    """The mechanism, per trace: same baseline, different sigma, so a different bar."""
    bg = np.flatnonzero(~sample["is_bouton"])
    higher = 0
    for j in bg:
        dff, rec = sample["dff"][:, j], sample["reconstruct"][:, j]
        base = calm_window_baseline(rec, FPS)
        higher += (base + 3 * noise_sigma_negative_tail(dff)
                   > base + 3 * noise_sigma_negative_tail(rec))
    assert higher == len(bg)


def test_reading_sigma_off_the_denoised_trace_fires_on_background(sample):
    """The trap, quantified: it fires on ROIs that cannot host events as often as on real ones."""
    trap = false_positive_rate("recon_own_sigma", sample["dff"], sample["reconstruct"],
                               sample["is_bouton"], FPS, clip_k=3.0)
    assert trap["false_positive_pct"] > 60.0


def test_the_arbitrated_variant_is_the_best_of_the_three(sample):
    """The claim. Not 'good': BEST, on this sample's own null population."""
    res = {r["variant"]: r["false_positive_pct"] for r in arbitrate(sample, clip_k=3.0)}
    assert res["arbitrated"] == min(res.values())
    assert res["arbitrated"] < res["recon_own_sigma"] / 4.0


def test_it_still_finds_the_real_events(sample):
    """A detector that fires on nothing would also pass the test above. This one must not."""
    b = np.flatnonzero(sample["is_bouton"])
    found = tot = 0
    for j in b:
        pk = detect("arbitrated", sample["dff"][:, j], sample["reconstruct"][:, j], FPS,
                    clip_k=3.0)
        true = sample["true_events"][j]
        tot += len(true)
        for fr in true:
            found += bool(np.any(np.abs(pk - fr) <= int(0.3 * FPS)))
    assert tot > 50
    assert found / tot > 0.5


def test_a_collapsed_denominator_returns_nothing():
    """The guard: a trace whose F0 collapsed is not a bouton with hundreds of events."""
    t = np.arange(int(20 * FPS)) / FPS
    insane = 1e4 * (1.0 + np.sin(2 * np.pi * 0.5 * t))
    pk = detect_events_arbitrated(insane, insane, fs=FPS, clip_k=3.0, guard=True)
    assert len(pk) == 0


def test_unknown_variant_is_refused(sample):
    with pytest.raises(ValueError):
        detect("median_plus_three", sample["dff"][:, 0], sample["reconstruct"][:, 0], FPS)


def test_same_seed_same_answer():
    a = make_sample(seed=7)
    b = make_sample(seed=7)
    assert np.allclose(a["dff"], b["dff"])
    assert np.allclose(a["reconstruct"], b["reconstruct"])


def test_rate_is_per_trace_per_second(sample):
    """population_rate must not scale with how many traces are in the mask."""
    m = sample["is_bouton"].copy()
    half = m.copy(); half[np.flatnonzero(m)[len(np.flatnonzero(m)) // 2:]] = False
    full = population_rate("arbitrated", sample["dff"], sample["reconstruct"], m, FPS)
    part = population_rate("arbitrated", sample["dff"], sample["reconstruct"], half, FPS)
    assert 0.3 < part / full < 3.0


def test_the_kernel_and_the_denoiser_are_sane():
    k = calcium_kernel(FPS)
    assert np.isclose(k.max(), 1.0) and k[0] < k.argmax()
    y = np.zeros(int(10 * FPS)); y[100] = 1.0
    out = denoise_ar1(y, FPS)
    assert out.max() > 0 and out.size == y.size


def test_every_variant_is_reachable(sample):
    for v in VARIANTS:
        pk = detect(v, sample["dff"][:, 0], sample["reconstruct"][:, 0], FPS)
        assert np.asarray(pk).ndim == 1
