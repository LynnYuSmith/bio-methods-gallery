"""A synthetic pair of z-stacks imaging the SAME field of view on two different days.

Day 1 (reference) and day 2 (moving) share the same tubular axon arbor and the same boutons,
but day 2 is displaced by a KNOWN 3-D shift — including a z-offset (the focal plane never
returns to exactly the same depth) — and carries independent noise plus a global brightness
change (the activity-dependent mean image drifts day to day). The true shift and the bouton
positions are known, so 2-D-only vs 3-D registration can be scored against ground truth.
"""
import numpy as np
from scipy.ndimage import gaussian_filter


def _draw_tube(vol, pts, radius=1.4, amp=1.0):
    """Paint a smooth tube through a list of 3-D control points (z, y, x) into ``vol``."""
    nz, ny, nx = vol.shape
    # densely interpolate the polyline, then splat a soft point at each step
    pts = np.asarray(pts, float)
    seg_t = np.linspace(0, 1, 400)
    idx = seg_t * (len(pts) - 1)
    lo = np.clip(idx.astype(int), 0, len(pts) - 2)
    frac = (idx - lo)[:, None]
    path = pts[lo] * (1 - frac) + pts[lo + 1] * frac
    for z, y, x in path:
        zi, yi, xi = int(round(z)), int(round(y)), int(round(x))
        if 0 <= zi < nz and 0 <= yi < ny and 0 <= xi < nx:
            vol[zi, yi, xi] += amp
    # a tube = the path dilated by a small 3-D Gaussian
    return gaussian_filter(vol, sigma=radius)


def make_stack(shape=(24, 100, 100), n_tubes=5, n_boutons=40, noise=0.04, seed=0):
    """Build ONE stack + its bouton centroids. Returns (stack, centroids[N,3] as [x,y,z])."""
    rng = np.random.RandomState(seed)
    nz, ny, nx = shape
    vol = np.zeros(shape, float)

    tubes = []
    for _ in range(n_tubes):
        # a tube wanders mostly in xy across a shallow z-band (like an axon in a thin FOV)
        z0 = rng.uniform(4, nz - 4)
        pts = []
        y, x = rng.uniform(15, ny - 15), rng.uniform(15, nx - 15)
        z = z0
        for _ in range(6):
            y = np.clip(y + rng.uniform(-25, 25), 8, ny - 8)
            x = np.clip(x + rng.uniform(-25, 25), 8, nx - 8)
            z = np.clip(z + rng.uniform(-2, 2), 3, nz - 3)
            pts.append((z, y, x))
        vol = _draw_tube(vol, pts, radius=1.3, amp=0.8)
        tubes.append(np.asarray(pts, float))

    # boutons: bright blobs sitting ON the tubes (interior only, so a small shift never wraps out)
    cents = []
    for _ in range(n_boutons):
        tube = tubes[rng.randint(len(tubes))]
        t = rng.uniform(0, 1)
        i = min(int(t * (len(tube) - 1)), len(tube) - 2)
        f = t * (len(tube) - 1) - i
        z, y, x = tube[i] * (1 - f) + tube[i + 1] * f
        if not (15 <= x <= nx - 15 and 15 <= y <= ny - 15 and 6 <= z <= nz - 6):
            continue
        zi, yi, xi = int(round(z)), int(round(y)), int(round(x))
        vol[zi, yi, xi] += 3.0
        cents.append((x, y, z))                       # project convention: [x, y, z]
    vol = gaussian_filter(vol, sigma=0.8)
    vol += rng.normal(0, noise, shape)
    return vol.astype(np.float32), np.asarray(cents, float)


def make_pair(true_shift=(3, -6, 5), brightness=1.6, noise=0.05, seed=0):
    """Return day-1 and day-2 stacks of the SAME FOV + ground truth.

    ``true_shift`` is ``(dz, dy, dx)`` in (planes, px, px): day-2 CONTENT is displaced by this,
    so the moving→reference SUBTRACT shift that registration should recover is exactly it. Day-2
    has independent noise and a ``brightness`` scale (mean-image drift). Returns a dict with
    ``ref``, ``mov`` (stacks), ``ref_cents``, ``mov_cents`` ([x,y,z]), and ``true`` = the shift."""
    ref, ref_cents = make_stack(noise=noise, seed=seed)
    dz, dy, dx = true_shift
    rng = np.random.RandomState(seed + 1)
    # day 2 = same arbor rolled by the true shift, brighter, with its OWN noise
    mov = np.roll(ref, shift=(dz, dy, dx), axis=(0, 1, 2)) * brightness
    mov = mov + rng.normal(0, noise, ref.shape)
    mov = mov.astype(np.float32)
    # the same boutons appear in day-2 at ref + (dx, dy, dz)  ([x,y,z] order)
    mov_cents = ref_cents + np.array([dx, dy, dz], float)
    return {"ref": ref, "mov": mov, "ref_cents": ref_cents, "mov_cents": mov_cents,
            "true": {"dx": float(dx), "dy": float(dy), "dz": float(dz)}}


if __name__ == "__main__":
    s = make_pair()
    print(f"ref {s['ref'].shape}, boutons {len(s['ref_cents'])}, true shift {s['true']}")
