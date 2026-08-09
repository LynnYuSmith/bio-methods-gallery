"""CLI: group motion-correct a TRAIN of Femtonics .mesc repeats → corrected .mesc each.

One shared reference is built from the first unit and handed to the whole train; the intensity
offset and pixel size are read from the files; the green channel drives the shift, applied to all.

    python -m mescmc rep1.mesc rep2.mesc rep3.mesc -o out/     # train → out/<stem>_MC.mesc
    python -m mescmc rep1.mesc --list                          # units, pixel size, offset, rate
    python -m mescmc rep1.mesc rep2.mesc -o out/ --max-shift-um 15
"""
import argparse

from .mesc_io import channel_offset, list_units
from .motion_correct import DEFAULT_MAX_SHIFT_UM, group_motion_correct_mesc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mescmc", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesc", nargs="+", help="input .mesc train (ordered; first unit = the anchor)")
    ap.add_argument("-o", "--out-dir", help="directory for the corrected <stem>_MC.mesc files")
    ap.add_argument("--list", action="store_true", help="list units (pixel size, offset, rate) and exit")
    ap.add_argument("--max-shift-um", type=float, default=DEFAULT_MAX_SHIFT_UM,
                    help=f"physical registration ceiling in µm (default {DEFAULT_MAX_SHIFT_UM})")
    ap.add_argument("--register-channel", default="Channel_0", help="channel to register on (green)")
    ap.add_argument("--sigma", type=float, default=4.0, help="high-pass sigma in px (default 4)")
    args = ap.parse_args(argv)

    if args.list or not args.out_dir:
        for p in args.mesc:
            for u in list_units(p):
                px = f"{u['pixel_um']:g} µm/px" if u["pixel_um"] else "pixel ?"
                fps = f"{u['frame_rate_hz']:.2f} Hz" if u["frame_rate_hz"] else "? Hz"
                off = channel_offset(p, u["path"], u["channels"][0])
                print(f"{p}:{u['path']}  {u['frames']}f  {'+'.join(u['channels'])}  "
                      f"{px}  offset {off:g}  {fps}")
        return 0

    for out in group_motion_correct_mesc(args.mesc, args.out_dir,
                                         register_channel=args.register_channel,
                                         max_shift_um=args.max_shift_um, sigma=args.sigma):
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
