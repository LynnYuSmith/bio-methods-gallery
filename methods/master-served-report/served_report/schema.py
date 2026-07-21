"""The HDF5 layout the server reads.

One file holds the whole experiment. The server never assumes anything beyond this layout, so any
file that follows it can be served, and the file itself is the unit of distribution.

    /metadata                        group; experiment-level attributes (id, date, indicator, ...)
    /groups/<area>/                  one group per imaging area
    /groups/<area>/polygons/<roi>    (n, 2) float; the ROI outline in pixel coordinates
    /units/<unit>/                   one group per recording unit
    /units/<unit>/roi_names          string dataset; the column order of the trace matrices
    /units/<unit>/traces/<kind>      (frames, rois) float; kind in {dff, deconvolved, raw, ...}

`examples/make_sample.py` writes a minimal file in this layout for the demo and the tests.
"""

TRACE_KINDS = ("dff", "deconvolved", "raw")
