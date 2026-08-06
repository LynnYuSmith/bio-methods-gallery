# mesc-reader

Read a Femtonics **.mesc** file and convert it to TIFF stacks or a plain HDF5, applying each
channel's **display conversion** — the PMT offset MESc itself subtracts — by default, and saying
so loudly. No *processing* beyond that: no motion correction, no background subtraction, no
rescaling the file doesn't already declare.

**Ownership tier:** hers / wrapper (a clean, minimal open reader of a documented on-disk layout;
the production pipeline's MESc handling is entangled with motion correction — a standalone reader
+ converter is the contribution).

![each channel's stored counts sit on a PMT offset (−786 green, −1170 red); applying the conversion drops the background to zero and leaves the signal](figures/before_after.png)

## The idea

A .mesc is just an **HDF5** file:

```
/MSession_i/MUnit_j                      one recording unit
    attrs: ZDim (frames), XDim, YDim,    dimensions
           ZAxisConversion…Scale (ms/frame → frame rate),
           XAxisConversion…Scale (µm/px),
           Channel_k_Conversion_ConversionLinearScale / …LinearOffset   per-channel display conversion
    Channel_0, Channel_1, …              (frames, height, width) arrays, one per channel
```

Each channel stores its counts on a **PMT offset**, and carries the conversion to undo it:
`physical = stored × scale + offset` (clipped at 0), with `offset` the dark-current baseline —
typically **−786** for green (Channel_0) and **−1170** for red (Channel_1). The native MESc reader
applies it; a reader that ignores it returns numbers ~786–1170 too high, *different from what a
collaborator sees*. So `mesc-reader`:

- **applies the conversion by default**, per channel, reading the coefficients from the file, and
  **warns loudly** which offset it used on which channel;
- lets you **set the coefficients by hand** (`scale=`, `offset=`) at read time;
- lets you ask for the **raw stored counts** (`apply_conversion=False`, or `--raw`) — no
  conversion, no warning.

Everything else is untouched: the frames are read exactly as stored, and the acquisition metadata
travels with them (into each TIFF's description and each HDF5 group).

## Use

```python
from mescreader import list_units, read_frames, channel_conversion, mesc_to_tiff, mesc_to_hdf5

for u in list_units("recording.mesc"):
    print(u["path"], u["frames"], u["frame_rate_hz"], u["conversion"])   # {'Channel_0': (1.0, -786.0), ...}

frames = read_frames("recording.mesc", "MSession_0/MUnit_0", "Channel_0")   # conversion applied + warns
raw    = read_frames("recording.mesc", "MSession_0/MUnit_0", "Channel_0", apply_conversion=False)
byhand = read_frames("recording.mesc", "MSession_0/MUnit_0", "Channel_0", offset=-786, scale=1.0)

mesc_to_tiff("recording.mesc", "out/")            # converted TIFFs (or apply_conversion=False)
mesc_to_hdf5("recording.mesc", "out.h5")          # a plain HDF5 mirror; applied coefficients recorded
```

CLI:

```bash
python -m mescreader recording.mesc --list                       # units + per-channel conversion
python -m mescreader recording.mesc --tiff out/                  # converted
python -m mescreader recording.mesc --hdf5 out.h5 --raw          # stored counts, no conversion
python -m mescreader recording.mesc --tiff out/ --offset -786    # set the conversion by hand
```

## Run the example

```bash
python -m venv .venv && source .venv/bin/activate    # Python 3.10+
pip install -e . && pip install pytest matplotlib && pip install -e ../../gallery_style
python examples/demo.py         # synthetic .mesc → shows the conversion per channel
pytest
```

## Notes

- The example uses a **synthetic** .mesc (same layout, a known frame pattern, realistic −786 /
  −1170 offsets) so the conversion and the round-trips can be checked against ground truth.
- If a channel's conversion attr is missing, the PMT defaults (−786 green / −1170 red) are used —
  and, as always, the warning tells you what was applied.
- The layout covers single- and multi-channel, single- and multi-unit files; every stored
  attribute is available via `read_metadata` and preserved by the HDF5 mirror.

## License

See `LICENSE`.
