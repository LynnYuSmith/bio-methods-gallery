"""CLI: convert a .mesc to raw TIFF stacks or a plain HDF5, or list its units.

    python -m mescreader FILE.mesc --list
    python -m mescreader FILE.mesc --tiff OUT_DIR
    python -m mescreader FILE.mesc --hdf5 OUT.h5
"""
import argparse

from .read import list_units, mesc_to_hdf5, mesc_to_tiff


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mescreader", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesc", help="path to the .mesc file")
    ap.add_argument("--list", action="store_true", help="list the units and exit")
    ap.add_argument("--tiff", metavar="DIR", help="write one raw TIFF stack per unit/channel")
    ap.add_argument("--hdf5", metavar="OUT.h5", help="write a plain HDF5 mirror of the raw frames")
    args = ap.parse_args(argv)

    if args.list or not (args.tiff or args.hdf5):
        for u in list_units(args.mesc):
            fps = f"{u['frame_rate_hz']:.2f} Hz" if u["frame_rate_hz"] else "?"
            print(f"{u['path']}  {u['frames']} frames  {u['height']}x{u['width']}  "
                  f"{fps}  channels={','.join(u['channels'])}")
        if not (args.tiff or args.hdf5):
            return 0
    if args.tiff:
        for p in mesc_to_tiff(args.mesc, args.tiff):
            print(f"wrote {p}")
    if args.hdf5:
        print(f"wrote {mesc_to_hdf5(args.mesc, args.hdf5)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
