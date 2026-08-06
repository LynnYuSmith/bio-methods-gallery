import numpy as np

from make_sample import make_pair
from xsession import register_2d, register_3d, match_boutons, FOVShift


def test_3d_recovers_the_known_shift_including_z():
    s = make_pair(true_shift=(3, -6, 5), seed=0)
    r = register_3d(s["ref"], s["mov"])
    t = s["true"]
    assert abs(r.dx - t["dx"]) < 1.0, r.dx
    assert abs(r.dy - t["dy"]) < 1.0, r.dy
    assert abs(r.dz_planes - t["dz"]) < 1.0, r.dz_planes      # the z axis xy-registration can't see
    assert r.xy_peak_corr > 0.5


def test_2d_recovers_xy_but_not_z():
    s = make_pair(true_shift=(3, -6, 5), seed=0)
    dx, dy, peak = register_2d(s["ref"].mean(0), s["mov"].mean(0))
    assert abs(dx - s["true"]["dx"]) < 1.0
    assert abs(dy - s["true"]["dy"]) < 1.0
    assert peak > 0.5
    # there is simply no z in a 2-D result — that absence is the whole point of the 3-D version


def test_3d_matches_boutons_that_2d_only_drops():
    # a z-offset larger than the z match radius: xy-only matching fails, 3-D matching succeeds
    s = make_pair(true_shift=(3, -6, 5), seed=1)
    N = len(s["ref_cents"])
    dx, dy, _ = register_2d(s["ref"].mean(0), s["mov"].mean(0))
    m2 = match_boutons(s["ref_cents"], s["mov_cents"],
                       FOVShift(dx=dx, dy=dy, dz_planes=0.0), radius_px=4.0, z_radius_planes=1.0)
    m3 = match_boutons(s["ref_cents"], s["mov_cents"],
                       register_3d(s["ref"], s["mov"]), radius_px=4.0, z_radius_planes=1.0)
    assert len(m3) > len(m2)                    # 3-D recovers the z-jittered boutons
    assert len(m3) >= 0.8 * N                   # and recovers most of them
    assert len(m2) <= 0.3 * N                   # xy-only leaves most unmatched


def test_matches_are_one_to_one_and_correct():
    # with the true shift, every reference bouton matches its own day-2 copy, no double-use
    s = make_pair(true_shift=(2, -3, 4), seed=2)
    t = s["true"]
    truth = FOVShift(dx=t["dx"], dy=t["dy"], dz_planes=t["dz"])
    pairs = match_boutons(s["ref_cents"], s["mov_cents"], truth, radius_px=2.0, z_radius_planes=1.0)
    ref_idx = [p[0] for p in pairs]; mov_idx = [p[1] for p in pairs]
    assert len(set(ref_idx)) == len(ref_idx)          # each reference bouton used once
    assert len(set(mov_idx)) == len(mov_idx)          # each moving bouton used once
    assert all(ri == mj for ri, mj in pairs)          # bouton i ↔ its own copy i
