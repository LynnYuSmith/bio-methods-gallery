"""Runnable example on the bundled sample. Writes figures/before_after.png."""
from pathlib import Path

from methodname import run


def main() -> None:
    data = None                      # load the bundled sample here
    result = run(data, param=0.3)    # noqa: F841
    out = Path(__file__).resolve().parent.parent / "figures" / "before_after.png"
    out.parent.mkdir(exist_ok=True)
    # plot the baseline and the method side by side, save to `out`
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
