"""What each gallery tile copies from the lab pipeline.

The gallery tiles are INDEPENDENT COPIES of the real pipeline functions — not parallel
reimplementations that drift and rot (a divergent copy is exactly how a standalone tool
ended up with bugs the live code never had). This manifest maps, per tile, the pipeline
source file + the symbols to lift into the tile's generated ``_synced.py``. Run
``python _sync/sync.py`` to (re)generate; ``--check`` to verify no drift.

Each entry:
    dest      : path (relative to the tile dir) of the generated module.
    header    : import lines the lifted symbols need (kept explicit — we copy bodies, not
                the source file's whole import soup).
    extracts  : [(source_relpath_in_pipeline, [symbol, ...]), ...] in output order.
    note      : one line for the generated module docstring.
"""
from __future__ import annotations

from pathlib import Path

# Default location of the private pipeline checkout: a sibling of the gallery repo, DERIVED from
# this file's own location (no hardcoded home path — this file is safe to publish). Override with
# `sync.py --repo <path>` or the PIPELINE_REPO env var; nothing here is a committed hard dependency.
_GALLERY_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DEFAULT = str(_GALLERY_ROOT.parent / "CalciumImagingPipeline" / "CalciumPipelineLib")

TILES: dict[str, dict] = {
    "dff-baseline": {
        "dest": "dffbaseline/_synced.py",
        "header": (
            "import numpy as np\n"
            "import pandas as pd\n"
            "from typing import Optional\n"
            "from scipy.ndimage import gaussian_filter1d\n"
        ),
        "extracts": [
            ("lib/signals/signal_processing.py", ["rolling_baseline", "maximin_baseline"]),
        ],
        "note": (
            "Real rolling-quantile baseline (with the auto clamp_below_signal footgun-fix and "
            "the light Gaussian post-smooth) and the suite2p maximin FLOOR baseline."
        ),
    },
    "osi-stats": {
        "dest": "osistats/_synced.py",
        "header": "import numpy as np\n",
        "extracts": [
            ("lib/analysis/selectivity.py", ["calculate_osi", "rayleigh_test"]),
        ],
        "note": (
            "Real OSI point estimate (direction→orientation folding + negative-response "
            "rectification, Mazurek 2014) and the Rayleigh non-uniformity test (n_obs sample "
            "size, NOT Kish's n_eff). The population shuffle+FDR call built on these is the "
            "tile's own contribution and lives in significance.py, not here."
        ),
    },
    "group-motion-correction": {
        "dest": "groupmc/_synced.py",
        "header": "import numpy as np\nfrom typing import Tuple\n",
        "extracts": [
            ("lib/roi/cross_session.py", ["_prep_image", "_alignment_peak_corr", "register_fov_xy"]),
        ],
        "note": (
            "Real sub-pixel FOV registration engine (phase cross-correlation + prep + "
            "post-alignment peak correlation). register_fov_xy returns the (dx, dy) shift in the "
            "project SUBTRACT convention (moving→reference displacement = NEGATIVE of skimage's "
            "align-shift) — the sign the whole pipeline keys on. The shared-reference group "
            "workflow that calls it is the tile's own and lives in register.py."
        ),
    },
}
