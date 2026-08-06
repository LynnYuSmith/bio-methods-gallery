"""CLI: convert a .mesc to TIFF stacks or a plain HDF5, or list its units.

By default the per-channel MESc display conversion (scale + offset, e.g. −786 green / −1170 red)
is applied — the values MESc shows. Use --raw for the stored counts, or --offset/--scale to set
the conversion by hand.

    python -m mescreader FILE.mesc --list
    python -m mescreader FILE.mesc --tiff OUT_DIR
    python -m mescreader FILE.mesc --hdf5 OUT.h5 --raw
    python -m mescreader FILE.mesc --tiff OUT_DIR --offset -786 --scale 1.0
"""
import argparse

from .read import list_units, mesc_to_hdf5, mesc_to_tiff


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mescreader", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesc", help="path to the .mesc file")
    ap.add_argument("--list", action="store_true", help="list the units (and conversions) and exit")
    ap.add_argument("--tiff", metavar="DIR", help="write one TIFF stack per unit/channel")
    ap.add_argument("--hdf5", metavar="OUT.h5", help="write a plain HDF5 mirror of the frames")
    ap.add_argument("--raw", action="store_true", help="stored counts, do NOT apply the conversion")
    ap.add_argument("--offset", type=float, default=None, help="override the conversion offset")
    ap.add_argument("--scale", type=float, default=None, help="override the conversion scale")
    args = ap.parse_args(argv)

    kw = dict(apply_conversion=not args.raw, scale=args.scale, offset=args.offset)

    if args.list or not (args.tiff or args.hdf5):
        for u in list_units(args.mesc):
            fps = f"{u['frame_rate_hz']:.2f} Hz" if u["frame_rate_hz"] else "?"
            conv = "  ".join(f"{ch}:(*{s:g}{o:+g})" for ch, (s, o) in u["conversion"].items())
            print(f"{u['path']}  {u['frames']} frames  {u['height']}x{u['width']}  {fps}  "
                  f"conversion {conv}")
        if not (args.tiff or args.hdf5):
            return 0
    if args.tiff:
        for p in mesc_to_tiff(args.mesc, args.tiff, **kw):
            print(f"wrote {p}")
    if args.hdf5:
        print(f"wrote {mesc_to_hdf5(args.mesc, args.hdf5, **kw)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
