"""Rigid motion correction by phase correlation — the primitive Suite2p uses for rigid registration.

Each frame is aligned to a reference by estimating a whole-frame translation ``(dy, dx)`` from the
**phase cross-correlation** of their FFTs, then shifting the frame back. A **high-pass** pre-filter
(subtract a Gaussian blur) makes the correlation lock onto structure — vessels, cell edges — instead
of the slow intensity envelope, which is what the production pipeline does (``phasecorr_method:
highpass``). The maximum allowed shift is a **physical** distance (µm) turned into pixels with the
recording's own pixel size, so it does not depend on the frame's pixel count.

Amplitude-blind to a constant offset: a flat PMT pedestal cancels in the phase spectrum, so
registration runs on the stored counts directly — no display conversion needed here.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, shift as nd_shift


def highpass(img: np.ndarray, sigma: float = 4.0) -> np.ndarray:
    """Structure-emphasising high-pass: ``img − gaussian_blur(img, sigma)`` (float)."""
    f = img.astype(np.float32)
    return f - gaussian_filter(f, sigma)


def _hann2d(shape: tuple[int, int]) -> np.ndarray:
    wy = np.hanning(shape[0])[:, None]
    wx = np.hanning(shape[1])[None, :]
    return (wy * wx).astype(np.float32)


def estimate_shift(reference: np.ndarray, frame: np.ndarray, *, sigma: float = 4.0) -> tuple[float, float]:
    """Sub-pixel translation ``(dy, dx)`` of ``frame`` relative to ``reference``.

    Phase correlation on the high-passed, Hann-windowed frames; the correlation peak is refined to
    sub-pixel by a parabolic fit on its immediate neighbours. The value is the displacement of
    ``frame`` — feed it (negated) to :func:`apply_shift` to bring the frame back onto the reference.
    """
    win = _hann2d(reference.shape)
    r = highpass(reference, sigma) * win
    g = highpass(frame, sigma) * win
    R = np.fft.rfft2(r)
    G = np.fft.rfft2(g)
    eps = np.abs(R) * np.abs(G)
    cross = R * np.conj(G)
    cross /= eps + 1e-8
    corr = np.fft.irfft2(cross, s=reference.shape)
    peak = np.unravel_index(int(np.argmax(corr)), corr.shape)

    shift = []
    for axis, p in enumerate(peak):
        n = corr.shape[axis]
        idx = [peak[0], peak[1]]
        idx[axis] = (p - 1) % n; cm = corr[tuple(idx)]
        idx[axis] = (p + 1) % n; cp = corr[tuple(idx)]
        c0 = corr[peak]
        denom = (cm - 2 * c0 + cp)
        sub = 0.5 * (cm - cp) / denom if denom != 0 else 0.0
        s = p + sub
        if s > n / 2:               # unwrap: a peak past the midpoint is a negative shift
            s -= n
        shift.append(float(s))
    # cross-power R·conj(G) peaks at −(displacement of `frame`); negate to report the displacement,
    # so apply_shift(frame, dy, dx) (which shifts by −dy,−dx) brings the frame back onto `reference`.
    return -shift[0], -shift[1]


def apply_shift(frame: np.ndarray, dy: float, dx: float) -> np.ndarray:
    """Shift ``frame`` back onto the reference by ``(−dy, −dx)``; preserves dtype (rounds for ints)."""
    out = nd_shift(frame.astype(np.float32), shift=(-dy, -dx), order=1, mode="nearest")
    if np.issubdtype(frame.dtype, np.integer):
        info = np.iinfo(frame.dtype)
        return np.clip(np.round(out), info.min, info.max).astype(frame.dtype)
    return out.astype(frame.dtype)


def build_reference(stack: np.ndarray, *, sigma: float = 4.0, max_shift_px: float = 40.0,
                    n_refine: int = 1) -> np.ndarray:
    """A registration reference: the mean, then ``n_refine`` passes of align-to-mean → re-mean.

    The refined mean is sharper than the raw mean (motion blur removed), so the per-frame shift
    estimates that follow are more accurate. Returns a float reference image.
    """
    ref = stack.mean(axis=0).astype(np.float32)
    for _ in range(max(0, n_refine)):
        acc = np.zeros_like(ref)
        for fr in stack:
            dy, dx = estimate_shift(ref, fr, sigma=sigma)
            dy, dx = _clamp(dy, dx, max_shift_px)
            acc += apply_shift(fr.astype(np.float32), dy, dx)
        ref = acc / len(stack)
    return ref


def _clamp(dy: float, dx: float, max_shift_px: float) -> tuple[float, float]:
    """Clamp a shift to a magnitude ceiling; a larger estimate is treated as spurious."""
    mag = float(np.hypot(dy, dx))
    if max_shift_px and mag > max_shift_px:
        k = max_shift_px / mag
        return dy * k, dx * k
    return dy, dx


def correct_stack(stack: np.ndarray, *, reference: np.ndarray | None = None, sigma: float = 4.0,
                  max_shift_px: float = 40.0) -> tuple[np.ndarray, np.ndarray]:
    """Motion-correct a ``(frames, H, W)`` stack.

    Returns ``(corrected, shifts)`` where ``shifts[i] = (dy, dx)`` is the applied displacement of
    frame *i* (clamped to ``max_shift_px``). If ``reference`` is None a refined reference is built.
    """
    if reference is None:
        reference = build_reference(stack, sigma=sigma, max_shift_px=max_shift_px)
    out = np.empty_like(stack)
    shifts = np.empty((len(stack), 2), dtype=np.float32)
    for i, fr in enumerate(stack):
        dy, dx = estimate_shift(reference, fr, sigma=sigma)
        dy, dx = _clamp(dy, dx, max_shift_px)
        out[i] = apply_shift(fr, dy, dx)
        shifts[i] = (dy, dx)
    return out, shifts


def residual_motion(stack: np.ndarray, *, reference: np.ndarray | None = None,
                    sigma: float = 4.0) -> float:
    """Mean per-frame displacement magnitude (px) to the reference — the motion left in a stack."""
    if reference is None:
        reference = stack.mean(axis=0).astype(np.float32)
    mags = [float(np.hypot(*estimate_shift(reference, fr, sigma=sigma))) for fr in stack]
    return float(np.mean(mags))
